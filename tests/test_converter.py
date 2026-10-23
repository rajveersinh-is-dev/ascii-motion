"""Unit tests for AsciiFrame and FrameConverter."""

import numpy as np

from ascii_motion.config import RenderConfig
from ascii_motion.core.converter import AsciiFrame, FrameConverter


def test_ascii_frame_to_text() -> None:
    chars = np.array([["A", "B"], ["C", "D"]], dtype="<U1")
    colors = np.zeros((2, 2, 3), dtype=np.uint8)
    frame = AsciiFrame(chars=chars, colors=colors, width=2, height=2)

    text = frame.to_text()
    assert text == "AB\nCD"


def test_ascii_frame_to_ansi() -> None:
    chars = np.array([["X"]], dtype="<U1")
    colors = np.array([[[255, 0, 0]]], dtype=np.uint8)
    frame = AsciiFrame(chars=chars, colors=colors, width=1, height=1)

    ansi = frame.to_ansi()
    assert "\033[38;2;255;0;0m" in ansi
    assert "X" in ansi


def test_frame_converter_dimensions() -> None:
    # 16:9 source (640x360), target_w = 60, char_aspect = 0.5
    # target_h = int(round((60 / (640/360)) * 0.5)) = 17
    cfg = RenderConfig(width=60, char_aspect_ratio=0.5)
    conv = FrameConverter(cfg)

    w, h = conv.calculate_dimensions(640, 360)
    assert w == 60
    assert h == 17

    # Explicit height override
    cfg_fixed = RenderConfig(width=80, height=30)
    conv_fixed = FrameConverter(cfg_fixed)
    w, h = conv_fixed.calculate_dimensions(1920, 1080)
    assert w == 80
    assert h == 30


def test_frame_converter_convert_frame() -> None:
    cfg = RenderConfig(width=40, style="monochrome", ramp_name="standard_10")
    conv = FrameConverter(cfg)

    # Convert pure black image
    black_img = np.zeros((100, 100, 3), dtype=np.uint8)
    frame = conv.convert_frame(black_img)

    assert frame.width == 40
    # First char in standard_10 is space (' ')
    assert frame.chars[0, 0] == " "

    # Convert pure white image
    white_img = np.full((100, 100, 3), 255, dtype=np.uint8)
    frame_white = conv.convert_frame(white_img)
    # Last char in standard_10 is '@'
    assert frame_white.chars[0, 0] == "@"
