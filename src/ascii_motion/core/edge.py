"""Vectorized Sobel edge detection and edge enhancement."""

from __future__ import annotations

import numpy as np


def compute_sobel_gradients(
    luminance: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute horizontal, vertical, and magnitude Sobel gradients.

    Implemented using pure vectorized NumPy array slicing for maximum speed
    without external computer vision library dependencies.

    Args:
        luminance: 2D float array in [0.0, 1.0].

    Returns:
        Tuple of (magnitude, gx, gy) arrays, each of shape (H, W).
    """
    h, w = luminance.shape
    gx = np.zeros_like(luminance)
    gy = np.zeros_like(luminance)

    if h < 3 or w < 3:
        return np.zeros_like(luminance), gx, gy

    # Vectorized 3x3 convolution via array slicing
    # Sobel X kernel: [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]]
    gx[1:-1, 1:-1] = (
        (luminance[:-2, 2:] + 2.0 * luminance[1:-1, 2:] + luminance[2:, 2:])
        - (luminance[:-2, :-2] + 2.0 * luminance[1:-1, :-2] + luminance[2:, :-2])
    ) / 4.0

    # Sobel Y kernel: [[-1, -2, -1], [0, 0, 0], [1, 2, 1]]
    gy[1:-1, 1:-1] = (
        (luminance[2:, :-2] + 2.0 * luminance[2:, 1:-1] + luminance[2:, 2:])
        - (luminance[:-2, :-2] + 2.0 * luminance[:-2, 1:-1] + luminance[:-2, 2:])
    ) / 4.0

    magnitude = np.sqrt(gx**2 + gy**2)
    # Normalize magnitude
    max_val = np.max(magnitude)
    if max_val > 0:
        magnitude = magnitude / max_val

    return magnitude.astype(np.float32), gx.astype(np.float32), gy.astype(np.float32)


def enhance_edges(
    luminance: np.ndarray,
    strength: float = 0.5,
) -> np.ndarray:
    """Enhance luminance contours and object boundaries using Sobel gradient magnitude.

    Args:
        luminance: 2D float array in [0.0, 1.0].
        strength: Edge enhancement multiplier (0.0 to 2.0).

    Returns:
        Enhanced float32 luminance array clipped to [0.0, 1.0].
    """
    if strength <= 0.0:
        return luminance

    magnitude, _, _ = compute_sobel_gradients(luminance)
    enhanced = luminance + strength * magnitude
    return np.clip(enhanced, 0.0, 1.0).astype(np.float32)


def get_directional_edge_chars(
    gx: np.ndarray,
    gy: np.ndarray,
    magnitude: np.ndarray,
    threshold: float = 0.3,
) -> np.ndarray:
    """Classify dominant edge orientations into ASCII strokes ('|', '-', '/', '\\').

    Args:
        gx: Horizontal gradient.
        gy: Vertical gradient.
        magnitude: Normalized gradient magnitude.
        threshold: Minimum gradient magnitude to qualify as an edge.

    Returns:
        2D array of single-character strings for significant edges, or empty space.
    """
    h, w = magnitude.shape
    out = np.full((h, w), " ", dtype="<U1")

    # Angles in degrees: [-180, 180]
    angles = np.rad2deg(np.arctan2(gy, gx)) % 180.0

    edge_mask = magnitude >= threshold

    # Horizontal edges (~0 or ~180 deg)
    horiz_mask = edge_mask & ((angles < 22.5) | (angles >= 157.5))
    out[horiz_mask] = "-"

    # Diagonal positive slope (~45 deg)
    diag_pos_mask = edge_mask & ((angles >= 22.5) & (angles < 67.5))
    out[diag_pos_mask] = "/"

    # Vertical edges (~90 deg)
    vert_mask = edge_mask & ((angles >= 67.5) & (angles < 112.5))
    out[vert_mask] = "|"

    # Diagonal negative slope (~135 deg)
    diag_neg_mask = edge_mask & ((angles >= 112.5) & (angles < 157.5))
    out[diag_neg_mask] = "\\"

    return out
