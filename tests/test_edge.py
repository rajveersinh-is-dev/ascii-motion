"""Unit tests for Sobel edge detection and edge enhancement."""

import numpy as np

from ascii_motion.core.edge import (
    compute_sobel_gradients,
    enhance_edges,
    get_directional_edge_chars,
)


def test_sobel_flat_image() -> None:
    flat = np.full((10, 10), 0.5, dtype=np.float32)
    mag, gx, gy = compute_sobel_gradients(flat)
    assert np.allclose(mag, 0.0)
    assert np.allclose(gx, 0.0)
    assert np.allclose(gy, 0.0)


def test_sobel_vertical_edge() -> None:
    img = np.zeros((10, 10), dtype=np.float32)
    img[:, 5:] = 1.0  # Vertical step boundary at x=5
    mag, gx, gy = compute_sobel_gradients(img)
    # The gradient should have a peak around x=4 or x=5
    assert np.max(mag[:, 4:6]) > 0.5
    # Vertical edge -> gx is strong, gy is near 0
    assert np.max(np.abs(gx)) > np.max(np.abs(gy))


def test_directional_edge_chars() -> None:
    mag = np.zeros((5, 5), dtype=np.float32)
    gx = np.zeros((5, 5), dtype=np.float32)
    gy = np.zeros((5, 5), dtype=np.float32)

    # Vertical line has horizontal gradient gx
    mag[2, 2] = 1.0
    gx[2, 2] = 1.0
    gy[2, 2] = 0.0

    chars = get_directional_edge_chars(gx, gy, mag, threshold=0.3)
    # Horizontal change -> boundary is horizontal or vertical? Angle = 0 deg
    assert chars[2, 2] in ("-", "|")


def test_enhance_edges() -> None:
    img = np.zeros((10, 10), dtype=np.float32)
    img[4:6, 4:6] = 1.0
    enhanced = enhance_edges(img, strength=0.5)
    assert enhanced.shape == (10, 10)
    assert np.all(enhanced >= 0.0)
    assert np.all(enhanced <= 1.0)
