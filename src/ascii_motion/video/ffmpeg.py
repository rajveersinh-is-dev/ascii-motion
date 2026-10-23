"""FFmpeg binary discovery and execution helpers."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


class FFmpegNotFoundError(RuntimeError):
    """Raised when FFmpeg cannot be located on the system."""

    pass


def get_ffmpeg_path() -> str:
    """Find the path to the FFmpeg executable.

    Checks in order:
    1. ASCII_MOTION_FFMPEG_PATH environment variable.
    2. System PATH via shutil.which('ffmpeg').
    3. imageio_ffmpeg bundled binary.

    Raises:
        FFmpegNotFoundError: If FFmpeg is not found anywhere.
    """
    # 1. Custom environment variable
    custom_path = os.environ.get("ASCII_MOTION_FFMPEG_PATH")
    if custom_path and Path(custom_path).is_file():
        return custom_path

    # 2. System PATH
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    # 3. imageio-ffmpeg
    try:
        import imageio_ffmpeg

        bundled = imageio_ffmpeg.get_ffmpeg_exe()
        if bundled and Path(bundled).is_file():
            return bundled
    except (ImportError, Exception):
        pass

    raise FFmpegNotFoundError(
        "FFmpeg executable not found. Please install FFmpeg on your system (e.g. via your package "
        "manager or 'winget install Gyan.FFmpeg'), install 'imageio-ffmpeg', or set the "
        "ASCII_MOTION_FFMPEG_PATH environment variable."
    )


def run_ffmpeg(
    args: list[str],
    capture_output: bool = True,
    timeout: float | None = 60.0,
) -> subprocess.CompletedProcess[str]:
    """Execute an FFmpeg command with safe argument array."""
    ffmpeg_exe = get_ffmpeg_path()
    cmd = [ffmpeg_exe, *args]
    return subprocess.run(
        cmd,
        capture_output=capture_output,
        text=True,
        timeout=timeout,
        check=False,
    )
