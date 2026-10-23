"""Integration tests for video probing, streaming reader, and FFmpeg error detection."""

from pathlib import Path

import pytest

from ascii_motion.config import RenderConfig
from ascii_motion.utils.synthetic import create_synthetic_video
from ascii_motion.video.probe import probe_video
from ascii_motion.video.reader import VideoStreamReader


@pytest.fixture(scope="module")
def sample_video(tmp_path_factory: pytest.TempPathFactory) -> Path:
    temp_dir = tmp_path_factory.mktemp("video_test")
    vid_path = temp_dir / "test_vid.mp4"
    create_synthetic_video(
        output_path=vid_path,
        duration=1.0,
        fps=20.0,
        width=320,
        height=180,
        include_audio=True,
    )
    return vid_path


def test_probe_valid_video(sample_video: Path) -> None:
    meta = probe_video(sample_video)
    assert meta.width == 320
    assert meta.height == 180
    assert pytest.approx(meta.duration, abs=0.2) == 1.0
    assert pytest.approx(meta.fps, abs=1.0) == 20.0
    assert meta.has_audio is True
    assert meta.video_codec == "h264"


def test_probe_nonexistent_file() -> None:
    with pytest.raises(FileNotFoundError):
        probe_video("nonexistent_video_path.mp4")


def test_probe_empty_file(tmp_path: Path) -> None:
    empty_file = tmp_path / "empty.mp4"
    empty_file.write_bytes(b"")
    with pytest.raises(ValueError, match="0 bytes"):
        probe_video(empty_file)


def test_probe_corrupt_file(tmp_path: Path) -> None:
    corrupt_file = tmp_path / "corrupt.mp4"
    corrupt_file.write_text("not a video header at all")
    with pytest.raises(ValueError, match="Could not parse valid video"):
        probe_video(corrupt_file)


def test_video_stream_reader(sample_video: Path) -> None:
    cfg = RenderConfig(width=40, target_fps=10.0, max_frames=5)
    meta = probe_video(sample_video)

    frames = []
    with VideoStreamReader(sample_video, cfg, meta) as reader:
        for f_idx, ts, arr in reader.frames():
            frames.append((f_idx, ts, arr))

    assert len(frames) == 5
    # First frame index is 0
    assert frames[0][0] == 0
    # Array has 3 channels
    assert frames[0][2].shape[2] == 3
