"""Vectorized Bayer ordered dithering and Floyd-Steinberg error diffusion."""

from __future__ import annotations

import numpy as np


def generate_bayer_matrix(order: int = 2) -> np.ndarray:
    """Recursively generate a normalized Bayer dither matrix from first principles.

    Order 1 generates a 2x2 matrix, Order 2 generates a 4x4 matrix,
    and Order 3 generates an 8x8 matrix.

    Returns:
        A 2D float32 numpy array with values in [0.0, 1.0].
    """
    matrix = np.array([[0]], dtype=np.float32)
    for _ in range(order):
        top_left = 4.0 * matrix
        top_right = 4.0 * matrix + 2.0
        bottom_left = 4.0 * matrix + 3.0
        bottom_right = 4.0 * matrix + 1.0
        top = np.hstack([top_left, top_right])
        bottom = np.hstack([bottom_left, bottom_right])
        matrix = np.vstack([top, bottom])

    # Normalize to [0.0, 1.0]
    total_elements = float(matrix.size)
    return (matrix / total_elements).astype(np.float32)


def apply_bayer_dithering(
    luminance: np.ndarray,
    num_levels: int,
    order: int = 2,
    strength: float = 0.5,
) -> np.ndarray:
    """Apply ordered Bayer dithering to a continuous luminance grid.

    Tiles the recursively generated Bayer matrix across the input grid and modulates
    the luminance by a fraction of the quantization step size.

    Args:
        luminance: 2D float array in [0.0, 1.0].
        num_levels: Number of discrete quantization levels (e.g. len of character ramp).
        order: Bayer matrix order (1 for 2x2, 2 for 4x4, 3 for 8x8).
        strength: Blending strength of dithering (0.0 to 1.0).

    Returns:
        Dithered float32 luminance array clipped to [0.0, 1.0].
    """
    if num_levels <= 1 or strength <= 0.0:
        return luminance

    bayer = generate_bayer_matrix(order)
    bh, bw = bayer.shape
    h, w = luminance.shape

    # Tile Bayer matrix across grid using vectorized indexing
    y_indices = np.arange(h) % bh
    x_indices = np.arange(w) % bw
    tiled_bayer = bayer[np.ix_(y_indices, x_indices)]

    # Step size between quantization levels
    step = 1.0 / max(num_levels - 1, 1)

    # Shift bayer to mean zero: [-0.5, 0.5] * step * strength
    offset = (tiled_bayer - 0.5) * step * strength
    dithered = luminance + offset
    return np.clip(dithered, 0.0, 1.0).astype(np.float32)


def apply_floyd_steinberg_dithering(
    luminance: np.ndarray,
    num_levels: int,
    strength: float = 0.8,
) -> np.ndarray:
    """Apply Floyd-Steinberg error diffusion dithering.

    Diffuses quantization error to adjacent future pixels using the classical weights:
    Right: 7/16, Down-Left: 3/16, Down: 5/16, Down-Right: 1/16.

    Args:
        luminance: 2D float array in [0.0, 1.0].
        num_levels: Number of quantization levels.
        strength: Error diffusion strength factor (0.0 to 1.0).

    Returns:
        Dithered float32 luminance array with diffused quantization error.
    """
    if num_levels <= 1 or strength <= 0.0:
        return luminance

    h, w = luminance.shape
    # Work on a floating point copy
    grid = np.copy(luminance).astype(np.float32)
    step = 1.0 / max(num_levels - 1, 1)

    for y in range(h):
        for x in range(w):
            old_val = grid[y, x]
            # Quantize to closest step
            quantized = np.clip(np.round(old_val / step) * step, 0.0, 1.0)
            err = (old_val - quantized) * strength
            grid[y, x] = quantized

            # Distribute error to neighbors
            if x + 1 < w:
                grid[y, x + 1] += err * (7.0 / 16.0)
            if y + 1 < h:
                if x - 1 >= 0:
                    grid[y + 1, x - 1] += err * (3.0 / 16.0)
                grid[y + 1, x] += err * (5.0 / 16.0)
                if x + 1 < w:
                    grid[y + 1, x + 1] += err * (1.0 / 16.0)

    return np.clip(grid, 0.0, 1.0).astype(np.float32)
