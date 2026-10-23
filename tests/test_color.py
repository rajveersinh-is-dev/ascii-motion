"""Unit tests for color handling, hex conversions, and palette remapping."""

import numpy as np

from ascii_motion.core.color import (
    hex_to_rgb,
    map_colors_to_palette,
    rgb_to_ansi256,
    rgb_to_hex,
)


def test_hex_to_rgb() -> None:
    assert hex_to_rgb("#FFFFFF") == (255, 255, 255)
    assert hex_to_rgb("#000000") == (0, 0, 0)
    assert hex_to_rgb("#FF0000") == (255, 0, 0)
    assert hex_to_rgb("00FF00") == (0, 255, 0)
    assert hex_to_rgb("#333") == (51, 51, 51)
    # Invalid defaults gracefully
    assert hex_to_rgb("invalid") == (255, 255, 255)


def test_rgb_to_hex() -> None:
    assert rgb_to_hex(255, 255, 255) == "#ffffff"
    assert rgb_to_hex(0, 0, 0) == "#000000"
    assert rgb_to_hex(255, 0, 128) == "#ff0080"


def test_rgb_to_ansi256() -> None:
    # Pure black -> index 16
    assert rgb_to_ansi256(0, 0, 0) == 16
    # Pure white -> index 231
    assert rgb_to_ansi256(255, 255, 255) == 231


def test_map_colors_to_palette() -> None:
    rgb = np.full((2, 2, 3), 128, dtype=np.uint8)
    lum = np.full((2, 2), 0.5, dtype=np.float32)

    # Color style returns unchanged rgb
    out_color = map_colors_to_palette(rgb, lum, style="color")
    assert np.array_equal(out_color, rgb)

    # Green style returns green tint
    out_green = map_colors_to_palette(rgb, lum, style="green")
    # Red should be ~25 (0x33 * 0.5), Green should be ~127 (0xFF * 0.5), Blue ~25
    assert out_green[0, 0, 1] > out_green[0, 0, 0]

    # Amber style returns amber tint (red > green > blue)
    out_amber = map_colors_to_palette(rgb, lum, style="amber")
    assert out_amber[0, 0, 0] > out_amber[0, 0, 1]
    assert out_amber[0, 0, 2] == 0
