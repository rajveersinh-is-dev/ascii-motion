"""Integration tests for all output exporters."""

from pathlib import Path

import numpy as np
import pytest

from ascii_motion.config import RenderConfig
from ascii_motion.core.converter import AsciiFrame
from ascii_motion.exporters.gif import export_to_gif
from ascii_motion.exporters.html import export_to_html
from ascii_motion.exporters.mp4 import export_to_mp4
from ascii_motion.exporters.terminal import play_in_terminal
from ascii_motion.exporters.text import export_to_text
from ascii_motion.video.probe import probe_video


@pytest.fixture
def mock_frames() -> list[AsciiFrame]:
    frames = []
    for i in range(5):
        chars = np.full((10, 20), "#", dtype="<U1")
        chars[0, 0] = str(i)
        colors = np.full((10, 20, 3), 100 + i * 20, dtype=np.uint8)
        frames.append(
            AsciiFrame(
                chars=chars, colors=colors, width=20, height=10, frame_index=i, timestamp=i * 0.1
            )
        )
    return frames


def test_export_to_html(mock_frames: list[AsciiFrame], tmp_path: Path) -> None:
    cfg = RenderConfig(width=20, height=10, style="color")
    out = tmp_path / "test.html"
    res = export_to_html(mock_frames, cfg, out, title="Test Player")

    assert res.is_file()
    assert res.stat().st_size > 500
    content = res.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "asciiCanvas" in content
    assert "Test Player" in content


def test_export_to_text(mock_frames: list[AsciiFrame], tmp_path: Path) -> None:
    out_plain = tmp_path / "test.txt"
    export_to_text(mock_frames, out_plain, include_ansi=False)
    assert out_plain.is_file()
    text = out_plain.read_text(encoding="utf-8")
    assert "#" in text

    out_ansi = tmp_path / "test.ans"
    export_to_text(mock_frames, out_ansi, include_ansi=True)
    assert out_ansi.is_file()
    ansi_text = out_ansi.read_text(encoding="utf-8")
    assert "\033[" in ansi_text


def test_export_to_gif(mock_frames: list[AsciiFrame], tmp_path: Path) -> None:
    cfg = RenderConfig(width=20, height=10, style="color")
    out_gif = tmp_path / "test.gif"
    res = export_to_gif(mock_frames, cfg, out_gif, fps=10.0)

    assert res.is_file()
    assert res.stat().st_size > 100


def test_export_to_mp4(mock_frames: list[AsciiFrame], tmp_path: Path) -> None:
    cfg = RenderConfig(width=20, height=10, style="color")
    out_mp4 = tmp_path / "test.mp4"
    res = export_to_mp4(mock_frames, cfg, out_mp4, fps=10.0)

    assert res.is_file()
    assert res.stat().st_size > 500

    # Probe the generated MP4 file to confirm readability
    meta = probe_video(res)
    assert meta.video_codec == "h264"
    assert meta.fps == 10.0


def test_play_in_terminal_non_interactive(mock_frames: list[AsciiFrame]) -> None:
    count = play_in_terminal(mock_frames, fps=30.0, loop=False)
    assert count == len(mock_frames)
