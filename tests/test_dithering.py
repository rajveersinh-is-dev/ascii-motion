"""Unit tests for Bayer ordered dithering and Floyd-Steinberg error diffusion."""

import numpy as np

from ascii_motion.core.dithering import (
    apply_bayer_dithering,
    apply_floyd_steinberg_dithering,
    generate_bayer_matrix,
)


def test_bayer_matrix_generation() -> None:
    # Order 1 -> 2x2
    m1 = generate_bayer_matrix(1)
    assert m1.shape == (2, 2)
    assert np.min(m1) == 0.0
    assert np.max(m1) < 1.0

    # Order 2 -> 4x4
    m2 = generate_bayer_matrix(2)
    assert m2.shape == (4, 4)

    # Order 3 -> 8x8
    m3 = generate_bayer_matrix(3)
    assert m3.shape == (8, 8)


def test_apply_bayer_dithering_bounds() -> None:
    lum = np.full((16, 16), 0.5, dtype=np.float32)
    dithered = apply_bayer_dithering(lum, num_levels=10, strength=0.5)
    assert dithered.shape == (16, 16)
    assert np.all(dithered >= 0.0)
    assert np.all(dithered <= 1.0)


def test_apply_floyd_steinberg_dithering() -> None:
    lum = np.linspace(0.0, 1.0, 25, dtype=np.float32).reshape((5, 5))
    dithered = apply_floyd_steinberg_dithering(lum, num_levels=5, strength=0.8)
    assert dithered.shape == (5, 5)
    assert np.all(dithered >= 0.0)
    assert np.all(dithered <= 1.0)
