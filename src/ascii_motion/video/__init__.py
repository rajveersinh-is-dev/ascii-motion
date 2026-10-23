"""Video decoding, probing, and streaming module."""

from ascii_motion.video.ffmpeg import FFmpegNotFoundError, get_ffmpeg_path, run_ffmpeg
from ascii_motion.video.probe import VideoMetadata, probe_video
from ascii_motion.video.reader import VideoStreamReader

__all__ = [
    "FFmpegNotFoundError",
    "get_ffmpeg_path",
    "run_ffmpeg",
    "VideoMetadata",
    "probe_video",
    "VideoStreamReader",
]
