"""Video metadata inspection and validation using FFmpeg."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ascii_motion.video.ffmpeg import get_ffmpeg_path


@dataclass(slots=True)
class VideoMetadata:
    """Inspected video file metadata."""

    path: str
    width: int
    height: int
    duration: float  # seconds
    fps: float
    total_frames: int
    has_audio: bool
    audio_codec: str | None = None
    video_codec: str | None = None
    rotation: int = 0  # degrees: 0, 90, 180, 270

    @property
    def aspect_ratio(self) -> float:
        """Width-to-height display aspect ratio."""
        return max(self.width, 1) / max(self.height, 1)


def probe_video(file_path: str | Path) -> VideoMetadata:
    """Probe video file and extract metadata.

    Args:
        file_path: Path to the target media file.

    Returns:
        VideoMetadata containing dimensions, duration, FPS, codecs, and audio status.

    Raises:
        FileNotFoundError: If the media file does not exist.
        ValueError: If the file is empty or contains no valid video stream.
    """
    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Media file not found: {path}")

    if path.stat().st_size == 0:
        raise ValueError(f"Media file is empty (0 bytes): {path}")

    ffmpeg_exe = get_ffmpeg_path()

    # ffmpeg -i <path> exits with code 1 and writes stream details to stderr
    cmd = [ffmpeg_exe, "-hide_banner", "-i", str(path)]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    combined_output = f"{result.stdout}\n{result.stderr}"

    # 1. Parse Duration
    dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", combined_output)
    if dur_match:
        hours = float(dur_match.group(1))
        minutes = float(dur_match.group(2))
        seconds = float(dur_match.group(3))
        duration = hours * 3600.0 + minutes * 60.0 + seconds
    else:
        duration = 0.0

    # 2. Parse Video Stream: dimensions and codec
    # e.g., Stream #0:0: Video: h264 (High), yuv420p, 1920x1080 [SAR 1:1 DAR 16:9], 30 fps
    video_match = re.search(
        r"Stream.*Video:\s*([^\s,]+)[^,]*,\s*[^,]+,\s*(\d{2,5})x(\d{2,5})",
        combined_output,
    )
    if not video_match:
        # Fallback search for dimensions
        dim_match = re.search(r"(\d{2,5})x(\d{2,5})", combined_output)
        if not dim_match:
            raise ValueError(
                f"Could not parse valid video stream from '{path.name}'. "
                "The file may be corrupt or an unsupported format."
            )
        video_codec = "unknown"
        width = int(dim_match.group(1))
        height = int(dim_match.group(2))
    else:
        video_codec = video_match.group(1).strip()
        width = int(video_match.group(2))
        height = int(video_match.group(3))

    # 3. Parse Frame Rate (fps or tbr)
    fps_match = re.search(r"(\d+(?:\.\d+)?)\s*fps", combined_output)
    if not fps_match:
        fps_match = re.search(r"(\d+(?:\.\d+)?)\s*tbr", combined_output)

    fps = float(fps_match.group(1)) if fps_match else 24.0
    if fps <= 0.0:
        fps = 24.0

    # 4. Total frame estimate
    total_frames = int(round(duration * fps)) if duration > 0 else 0

    # 5. Parse Audio Stream
    audio_match = re.search(r"Stream.*Audio:\s*([^\s,]+)", combined_output)
    has_audio = audio_match is not None
    audio_codec = audio_match.group(1).strip() if audio_match else None

    # 6. Parse Rotation metadata
    rotation = 0
    rot_match = re.search(r"rotation of\s*(-?\d+)", combined_output)
    if not rot_match:
        rot_match = re.search(r"rotate\s*:\s*(\d+)", combined_output)
    if rot_match:
        rotation = int(rot_match.group(1)) % 360

    # If rotated 90 or 270 degrees, display dimensions are swapped
    if rotation in (90, 270):
        width, height = height, width

    return VideoMetadata(
        path=str(path),
        width=width,
        height=height,
        duration=duration,
        fps=fps,
        total_frames=total_frames,
        has_audio=has_audio,
        audio_codec=audio_codec,
        video_codec=video_codec,
        rotation=rotation,
    )
