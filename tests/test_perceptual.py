"""Unit tests for perceptual luminance, tone mapping, and temporal smoothing."""

import numpy as np
import pytest

from ascii_motion.core.perceptual import (
    adjust_tone,
    apply_temporal_smoothing,
    rgb_to_luminance,
)


def test_rgb_to_luminance_black_and_white() -> None:
    black = np.zeros((2, 2, 3), dtype=np.uint8)
    lum_black = rgb_to_luminance(black)
    assert np.allclose(lum_black, 0.0)

    white = np.full((2, 2, 3), 255, dtype=np.uint8)
    lum_white = rgb_to_luminance(white)
    assert np.allclose(lum_white, 1.0)


def test_rgb_to_luminance_standards() -> None:
    # Pure green: Rec. 709 gives 0.7152, Rec. 601 gives 0.5870
    green = np.zeros((1, 1, 3), dtype=np.float32)
    green[0, 0, 1] = 1.0

    lum_709 = rgb_to_luminance(green, standard="bt709")
    assert pytest.approx(float(lum_709[0, 0]), abs=1e-3) == 0.7152

    lum_601 = rgb_to_luminance(green, standard="bt601")
    assert pytest.approx(float(lum_601[0, 0]), abs=1e-3) == 0.5870

    lum_avg = rgb_to_luminance(green, standard="average")
    assert pytest.approx(float(lum_avg[0, 0]), abs=1e-3) == 0.3333


def test_adjust_tone_brightness_and_contrast() -> None:
    lum = np.array([[0.2, 0.5, 0.8]], dtype=np.float32)

    # Brightness doubling
    brighter = adjust_tone(lum, brightness=2.0)
    assert pytest.approx(float(brighter[0, 0])) == 0.4
    assert pytest.approx(float(brighter[0, 1])) == 1.0
    assert pytest.approx(float(brighter[0, 2])) == 1.0  # clipped at 1.0

    # Invert
    inverted = adjust_tone(lum, invert=True)
    assert pytest.approx(float(inverted[0, 0])) == 0.8
    assert pytest.approx(float(inverted[0, 1])) == 0.5
    assert pytest.approx(float(inverted[0, 2])) == 0.2


def test_adjust_tone_gamma() -> None:
    lum = np.array([[0.25]], dtype=np.float32)
    # gamma = 2.0 -> out = 0.25^(1/2) = 0.5
    corrected = adjust_tone(lum, gamma=2.0)
    assert pytest.approx(float(corrected[0, 0]), abs=1e-4) == 0.5


def test_temporal_smoothing() -> None:
    prev = np.full((2, 2), 0.2, dtype=np.float32)
    curr = np.full((2, 2), 0.3, dtype=np.float32)

    # alpha = 0.5, small delta -> blend
    smoothed = apply_temporal_smoothing(curr, prev, alpha=0.5, motion_threshold=0.5)
    assert pytest.approx(float(smoothed[0, 0]), abs=0.05) == 0.25

    # First frame (no prev)
    first = apply_temporal_smoothing(curr, None, alpha=0.5)
    assert np.allclose(first, curr)
