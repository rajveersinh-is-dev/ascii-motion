"""Background job coordinator for asynchronous video-to-ASCII rendering."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from ascii_motion.config import RenderConfig
from ascii_motion.core.converter import FrameConverter
from ascii_motion.exporters.gif import export_to_gif
from ascii_motion.exporters.html import export_to_html
from ascii_motion.exporters.mp4 import export_to_mp4
from ascii_motion.exporters.text import export_to_text
from ascii_motion.video.probe import probe_video
from ascii_motion.video.reader import VideoStreamReader


@dataclass
class Job:
    """Represents an asynchronous rendering task."""

    job_id: str
    input_path: Path
    export_format: str  # 'mp4', 'html', 'gif', 'txt', 'ans'
    config: RenderConfig
    status: str = "pending"  # 'pending', 'processing', 'completed', 'failed', 'cancelled'
    progress: float = 0.0  # 0.0 to 100.0
    processed_frames: int = 0
    total_frames: int = 0
    output_path: Path | None = None
    error_message: str | None = None
    cancel_requested: bool = False
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None


class JobManager:
    """Thread-safe manager for conversion jobs."""

    def __init__(self, work_dir: Path | str | None = None) -> None:
        self.work_dir = Path(work_dir or Path.cwd() / "tmp" / "jobs").resolve()
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()

    def create_job(
        self,
        input_path: Path,
        export_format: str,
        config: RenderConfig,
    ) -> Job:
        """Create and register a new job."""
        job_id = str(uuid.uuid4())
        job = Job(
            job_id=job_id,
            input_path=input_path,
            export_format=export_format.lower().lstrip("."),
            config=config,
        )
        with self.lock:
            self.jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Job | None:
        """Retrieve job by ID."""
        with self.lock:
            return self.jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        """Signal job cancellation."""
        with self.lock:
            job = self.jobs.get(job_id)
            if job and job.status in ("pending", "processing"):
                job.cancel_requested = True
                job.status = "cancelled"
                return True
        return False

    def run_job_sync(self, job: Job) -> None:
        """Execute a rendering job synchronously in a background thread."""
        try:
            job.status = "processing"
            meta = probe_video(job.input_path)

            effective_fps = job.config.target_fps or meta.fps
            effective_duration = meta.duration
            if job.config.max_duration and job.config.max_duration < effective_duration:
                effective_duration = job.config.max_duration

            job.total_frames = max(1, int(round(effective_duration * effective_fps)))
            if job.config.max_frames and job.config.max_frames < job.total_frames:
                job.total_frames = job.config.max_frames

            converter = FrameConverter(job.config)
            frames = []

            job_out_dir = self.work_dir / job.job_id
            job_out_dir.mkdir(parents=True, exist_ok=True)
            output_file = job_out_dir / f"ascii_output.{job.export_format}"

            with VideoStreamReader(job.input_path, job.config, meta) as reader:
                for idx, ts, raw_arr in reader.frames():
                    if job.cancel_requested:
                        job.status = "cancelled"
                        return

                    frame = converter.convert_frame(raw_arr, idx, ts)
                    frames.append(frame)
                    job.processed_frames = len(frames)
                    job.progress = min(95.0, (len(frames) / job.total_frames) * 90.0)

            if job.cancel_requested:
                job.status = "cancelled"
                return

            if not frames:
                raise RuntimeError("No frames could be extracted from video.")

            job.progress = 95.0

            # Export phase
            if job.export_format in ("mp4", "mov", "mkv"):
                export_to_mp4(
                    frames,
                    job.config,
                    output_file,
                    source_video=job.input_path,
                    fps=effective_fps,
                )
            elif job.export_format in ("html", "htm"):
                export_to_html(
                    frames,
                    job.config,
                    output_file,
                    title=f"ascii-motion: {job.input_path.name}",
                )
            elif job.export_format == "gif":
                export_to_gif(frames, job.config, output_file, fps=effective_fps)
            elif job.export_format in ("txt", "ans"):
                is_ansi = job.export_format == "ans" or job.config.style != "monochrome"
                export_to_text(frames, output_file, include_ansi=is_ansi)
            else:
                export_to_html(frames, job.config, output_file)

            job.output_path = output_file
            job.progress = 100.0
            job.status = "completed"
            job.completed_at = time.time()

        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)
        finally:
            if job.cancel_requested:
                job.status = "cancelled"
                if job.output_path and job.output_path.is_file():
                    try:
                        job.output_path.unlink()
                    except OSError:
                        pass

    def start_job(self, job: Job) -> None:
        """Launch job in background thread."""
        thread = threading.Thread(target=self.run_job_sync, args=(job,), daemon=True)
        thread.start()


# Global default instance
job_manager = JobManager()
