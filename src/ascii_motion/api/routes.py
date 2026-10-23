"""FastAPI routes for ascii-motion web API."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ascii_motion.api.jobs import job_manager
from ascii_motion.config import RenderConfig
from ascii_motion.core.converter import FrameConverter
from ascii_motion.core.ramps import PREDEFINED_RAMPS
from ascii_motion.utils.synthetic import create_synthetic_video
from ascii_motion.video.probe import probe_video
from ascii_motion.video.reader import VideoStreamReader

router = APIRouter(prefix="/api")

UPLOAD_DIR = (Path.cwd() / "tmp" / "uploads").resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_VIDEO_PATH = (Path.cwd() / "assets" / "sample_video.mp4").resolve()


class PreviewRequest(BaseModel):
    video_path: str
    timestamp: float = 0.0
    config: RenderConfig


class PreviewResponse(BaseModel):
    width: int
    height: int
    lines: list[str]
    colors: list[list[str]] | None = None
    style: str
    background_color: str
    foreground_color: str


class ConvertRequest(BaseModel):
    video_path: str
    export_format: str = Field(default="mp4", description="mp4, html, gif, txt, or ans")
    config: RenderConfig


@router.get("/ramps")
def list_ramps() -> dict[str, str]:
    """Get list of available predefined character ramps."""
    return PREDEFINED_RAMPS


@router.get("/sample")
def get_sample_video() -> dict[str, Any]:
    """Provide a verified synthetic sample video for immediate testing."""
    SAMPLE_VIDEO_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not SAMPLE_VIDEO_PATH.is_file() or SAMPLE_VIDEO_PATH.stat().st_size == 0:
        create_synthetic_video(
            SAMPLE_VIDEO_PATH,
            duration=2.0,
            fps=20.0,
            width=640,
            height=360,
            include_audio=True,
        )

    meta = probe_video(SAMPLE_VIDEO_PATH)
    return {
        "path": str(SAMPLE_VIDEO_PATH),
        "filename": SAMPLE_VIDEO_PATH.name,
        "metadata": {
            "width": meta.width,
            "height": meta.height,
            "duration": meta.duration,
            "fps": meta.fps,
            "total_frames": meta.total_frames,
            "has_audio": meta.has_audio,
            "video_codec": meta.video_codec,
            "audio_codec": meta.audio_codec,
        },
    }


@router.post("/upload")
async def upload_video(file: UploadFile = File(...)) -> dict[str, Any]:
    """Handle video file upload safely with server-side validation."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing.")

    # Sanitize extension
    ext = Path(file.filename).suffix.lower()
    if ext not in (".mp4", ".mov", ".webm", ".avi", ".mkv", ".m4v"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video format '{ext}'. Allowed: .mp4, .mov, .webm, .avi, .mkv",
        )

    safe_name = f"{uuid.uuid4().hex[:12]}{ext}"
    saved_path = UPLOAD_DIR / safe_name

    try:
        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {exc}") from exc

    try:
        meta = probe_video(saved_path)
    except Exception as exc:
        if saved_path.is_file():
            saved_path.unlink()
        raise HTTPException(status_code=400, detail=f"Invalid video file: {exc}") from exc

    return {
        "path": str(saved_path),
        "filename": file.filename,
        "metadata": {
            "width": meta.width,
            "height": meta.height,
            "duration": meta.duration,
            "fps": meta.fps,
            "total_frames": meta.total_frames,
            "has_audio": meta.has_audio,
            "video_codec": meta.video_codec,
            "audio_codec": meta.audio_codec,
        },
    }


@router.post("/preview", response_model=PreviewResponse)
def generate_preview(req: PreviewRequest) -> PreviewResponse:
    """Generate a high-speed single frame ASCII preview for interactive UI tuning."""
    path = Path(req.video_path).resolve()
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Video file not found.")

    try:
        meta = probe_video(path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Cannot inspect video: {exc}") from exc

    # Configure reader for single frame at timestamp
    cfg = req.config.model_copy()
    cfg.trim_start = max(0.0, min(req.timestamp, max(0.0, meta.duration - 0.1)))
    cfg.max_frames = 1

    converter = FrameConverter(cfg)
    target_frame = None

    try:
        with VideoStreamReader(path, cfg, meta) as reader:
            for idx, ts, raw_arr in reader.frames():
                target_frame = converter.convert_frame(raw_arr, idx, ts)
                break
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate frame: {exc}") from exc

    if target_frame is None:
        raise HTTPException(
            status_code=400, detail="Could not read frame from specified timestamp."
        )

    lines = ["".join(row) for row in target_frame.chars]

    # Cell colors if color style requested
    colors: list[list[str]] | None = None
    if cfg.style == "color":
        colors = []
        for y in range(target_frame.height):
            row_colors = [
                f"#{target_frame.colors[y, x, 0]:02x}{target_frame.colors[y, x, 1]:02x}{target_frame.colors[y, x, 2]:02x}"
                for x in range(target_frame.width)
            ]
            colors.append(row_colors)

    return PreviewResponse(
        width=target_frame.width,
        height=target_frame.height,
        lines=lines,
        colors=colors,
        style=cfg.style,
        background_color=cfg.background_color,
        foreground_color=cfg.foreground_color,
    )


@router.post("/convert")
def start_conversion(req: ConvertRequest) -> dict[str, str]:
    """Start an asynchronous background rendering job."""
    path = Path(req.video_path).resolve()
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Input video file not found.")

    job = job_manager.create_job(
        input_path=path,
        export_format=req.export_format,
        config=req.config,
    )
    job_manager.start_job(job)
    return {"job_id": job.job_id}


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str) -> dict[str, Any]:
    """Poll progress status of a conversion job."""
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    return {
        "job_id": job.job_id,
        "status": job.status,
        "progress": round(job.progress, 1),
        "processed_frames": job.processed_frames,
        "total_frames": job.total_frames,
        "error": job.error_message,
        "output_available": job.output_path is not None and job.output_path.is_file(),
    }


@router.post("/jobs/{job_id}/cancel")
def cancel_conversion_job(job_id: str) -> dict[str, bool]:
    """Cancel a running job."""
    success = job_manager.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel job (not active or not found).")
    return {"success": True}


@router.get("/jobs/{job_id}/download")
def download_job_output(job_id: str) -> FileResponse:
    """Download the completed output file of a job."""
    job = job_manager.get_job(job_id)
    if not job or not job.output_path or not job.output_path.is_file():
        raise HTTPException(status_code=404, detail="Job output not ready or not found.")

    filename = f"ascii_motion_{job.input_path.stem}.{job.export_format}"
    return FileResponse(
        path=job.output_path,
        filename=filename,
        media_type="application/octet-stream",
    )
