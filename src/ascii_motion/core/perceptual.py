"""Perceptually accurate luminance calculation and tone mapping."""

from __future__ import annotations

import numpy as np

# ITU-R BT.709 coefficients (standard for sRGB and HDTV)
BT709_R = 0.2126
BT709_G = 0.7152
BT709_B = 0.0722

# ITU-R BT.601 coefficients (standard for SDTV)
BT601_R = 0.2990
BT601_G = 0.5870
BT601_B = 0.1140


def rgb_to_luminance(
    rgb: np.ndarray,
    standard: str = "bt709",
) -> np.ndarray:
    """Calculate perceptual luminance from an RGB array.

    Args:
        rgb: Numpy array of shape (..., 3), either uint8 [0, 255] or float [0, 1].
        standard: 'bt709' (default), 'bt601', or 'average'.

    Returns:
        Float32 array of shape (...) with luminance values normalized to [0.0, 1.0].
    """
    if rgb.dtype == np.uint8:
        rgb_float = rgb.astype(np.float32) / 255.0
    else:
        rgb_float = np.asarray(rgb, dtype=np.float32)

    r = rgb_float[..., 0]
    g = rgb_float[..., 1]
    b = rgb_float[..., 2]

    if standard == "bt709":
        lum = BT709_R * r + BT709_G * g + BT709_B * b
    elif standard == "bt601":
        lum = BT601_R * r + BT601_G * g + BT601_B * b
    elif standard == "average":
        lum = (r + g + b) / 3.0
    else:
        raise ValueError(f"Unknown standard: {standard}. Choose 'bt709', 'bt601', or 'average'.")

    return np.clip(lum, 0.0, 1.0)


def adjust_tone(
    luminance: np.ndarray,
    brightness: float = 1.0,
    contrast: float = 1.0,
    gamma: float = 1.0,
    invert: bool = False,
) -> np.ndarray:
    """Apply tone mapping adjustments: brightness, contrast, gamma, and inversion.

    All operations are fully vectorized using NumPy.

    Args:
        luminance: Float array of luminance in range [0.0, 1.0].
        brightness: Multiplier factor (1.0 = neutral, >1.0 = brighter, <1.0 = darker).
        contrast: Contrast factor (1.0 = neutral, >1.0 = higher contrast, <1.0 = flatter).
        gamma: Gamma exponent (1.0 = neutral, >1.0 = lift shadows, <1.0 = darken midtones).
        invert: If True, reverses luminance (0 becomes 1, 1 becomes 0).

    Returns:
        Adjusted float32 luminance array clipped to [0.0, 1.0].
    """
    out = np.copy(luminance)

    # 1. Brightness
    if brightness != 1.0:
        out = out * brightness

    # 2. Contrast centered at 0.5
    if contrast != 1.0:
        out = (out - 0.5) * contrast + 0.5

    # 3. Clip before gamma to avoid negative powers / NaN
    out = np.clip(out, 0.0, 1.0)

    # 4. Gamma correction
    if gamma != 1.0 and gamma > 0.0:
        # Applying standard power law: out = out^(1/gamma)
        out = np.power(out, 1.0 / gamma)

    # 5. Inversion
    if invert:
        out = 1.0 - out

    return np.clip(out, 0.0, 1.0).astype(np.float32)


def apply_temporal_smoothing(
    current_lum: np.ndarray,
    previous_lum: np.ndarray | None,
    alpha: float = 0.0,
    motion_threshold: float = 0.25,
) -> np.ndarray:
    """Apply temporal stabilization between successive frames.

    Blends the current luminance with the previous luminance to suppress high-frequency
    ASCII flickering in static/subtle areas, while selectively relaxing smoothing when
    large motion (differences exceeding motion_threshold) occurs.

    Args:
        current_lum: Current frame luminance array.
        previous_lum: Previous frame luminance array (or None if first frame).
        alpha: Smoothing factor in [0.0, 0.9]. 0.0 = no smoothing.
        motion_threshold: Luminance delta beyond which temporal dampening is reduced.

    Returns:
        Stabilized luminance array.
    """
    if previous_lum is None or alpha <= 0.0 or previous_lum.shape != current_lum.shape:
        return current_lum

    # Compute per-pixel difference
    delta = np.abs(current_lum - previous_lum)

    # Where motion is large, decay alpha towards zero to avoid ghosting/trails
    motion_mask = np.clip(delta / max(motion_threshold, 1e-4), 0.0, 1.0)
    effective_alpha = alpha * (1.0 - motion_mask)

    # Stabilized luminance
    stabilized = (1.0 - effective_alpha) * current_lum + effective_alpha * previous_lum
    return np.clip(stabilized, 0.0, 1.0).astype(np.float32)
