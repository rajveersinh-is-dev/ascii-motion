"""Streaming video frame reader using FFmpeg subprocessing."""

from __future__ import annotations

import subprocess
from collections.abc import Generator
from pathlib import Path
from typing import Any

import numpy as np

from ascii_motion.config import RenderConfig
from ascii_motion.video.ffmpeg import get_ffmpeg_path
from ascii_motion.video.probe import VideoMetadata, probe_video


class VideoStreamReader:
    """Streams decoded video frames from FFmpeg with bounded memory and optional downscaling."""

    def __init__(
        self,
        video_path: str | Path,
        config: RenderConfig,
        metadata: VideoMetadata | None = None,
    ) -> None:
        self.video_path = Path(video_path).resolve()
        self.config = config
        self.metadata = metadata or probe_video(self.video_path)
        self.process: subprocess.Popen[bytes] | None = None

        # Decode size: preserve natural source aspect ratio at roughly 2x character resolution
        target_w = config.width
        self.decode_w = min(self.metadata.width, max(target_w * 2, target_w))
        if self.decode_w % 2 != 0:
            self.decode_w += 1

        self.decode_h = min(
            self.metadata.height,
            max(int(round(self.decode_w / self.metadata.aspect_ratio)), 2),
        )
        if self.decode_h % 2 != 0:
            self.decode_h += 1

        # Effective frame rate
        self.fps = config.target_fps or self.metadata.fps
        if self.fps <= 0.0:
            self.fps = 24.0

        self.frame_bytes = self.decode_w * self.decode_h * 3

    def __enter__(self) -> VideoStreamReader:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def frames(self) -> Generator[tuple[int, float, np.ndarray], None, None]:
        """Yield (frame_index, timestamp_seconds, rgb_uint8_ndarray) sequentially.

        Only one frame is in memory at a time.
        """
        ffmpeg_exe = get_ffmpeg_path()

        cmd: list[str] = [
            ffmpeg_exe,
            "-hide_banner",
            "-loglevel",
            "error",
        ]

        # Fast seek to trim start if specified
        if self.config.trim_start > 0.0:
            cmd.extend(["-ss", f"{self.config.trim_start:.3f}"])

        cmd.extend(["-i", str(self.video_path)])

        # Max duration limit
        effective_duration = None
        if self.config.trim_end is not None and self.config.trim_end > self.config.trim_start:
            effective_duration = self.config.trim_end - self.config.trim_start
        if self.config.max_duration is not None:
            if effective_duration is None or self.config.max_duration < effective_duration:
                effective_duration = self.config.max_duration

        if effective_duration is not None and effective_duration > 0:
            cmd.extend(["-t", f"{effective_duration:.3f}"])

        # Video filters: fps sampling and scaling
        vf_filters: list[str] = []
        if (
            self.config.target_fps is not None
            and abs(self.config.target_fps - self.metadata.fps) > 0.01
        ):
            vf_filters.append(f"fps={self.fps:.3f}")

        vf_filters.append(f"scale={self.decode_w}:{self.decode_h}")

        if vf_filters:
            cmd.extend(["-vf", ",".join(vf_filters)])

        # Output rawvideo rgb24 to pipe
        cmd.extend(
            [
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-",
            ]
        )

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=10 * self.frame_bytes,
        )

        frame_idx = 0
        frame_interval = 1.0 / self.fps

        try:
            assert self.process.stdout is not None
            while True:
                if self.config.max_frames is not None and frame_idx >= self.config.max_frames:
                    break

                raw_bytes = self.process.stdout.read(self.frame_bytes)
                if len(raw_bytes) < self.frame_bytes:
                    break  # End of stream

                # Reshape raw bytes to (H, W, 3) uint8 numpy array
                frame_arr = np.frombuffer(raw_bytes, dtype=np.uint8).reshape(
                    (self.decode_h, self.decode_w, 3)
                )

                timestamp = self.config.trim_start + (frame_idx * frame_interval)
                yield frame_idx, timestamp, frame_arr
                frame_idx += 1
        finally:
            self.close()

    def close(self) -> None:
        """Terminate the decoding subprocess safely."""
        if self.process is not None:
            try:
                if self.process.stdout:
                    self.process.stdout.close()
                if self.process.stderr:
                    self.process.stderr.close()
                self.process.terminate()
                self.process.wait(timeout=2.0)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    self.process.kill()
                except OSError:
                    pass
            finally:
                self.process = None
