"""Color handling, retro terminal palettes, and ANSI/HTML color formatting."""

from __future__ import annotations

import numpy as np


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    """Convert a hex color string ('#RRGGBB' or 'RRGGBB') to an (R, G, B) tuple."""
    cleaned = hex_str.lstrip("#")
    if len(cleaned) == 3:
        cleaned = "".join(c * 2 for c in cleaned)
    if len(cleaned) != 6:
        return 255, 255, 255
    try:
        r = int(cleaned[0:2], 16)
        g = int(cleaned[2:4], 16)
        b = int(cleaned[4:6], 16)
        return r, g, b
    except ValueError:
        return 255, 255, 255


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert (R, G, B) integers [0, 255] to a '#RRGGBB' hex string."""
    return (
        f"#{int(np.clip(r, 0, 255)):02x}{int(np.clip(g, 0, 255)):02x}{int(np.clip(b, 0, 255)):02x}"
    )


def rgb_to_ansi256(r: int, g: int, b: int) -> int:
    """Map an (R, G, B) color to the standard xterm 256-color palette index."""
    # Check if close to grayscale
    if abs(r - g) < 8 and abs(g - b) < 8:
        # Grayscale ramp is 232 to 255 (24 shades from 8 to 238)
        gray = (r + g + b) // 3
        if gray < 8:
            return 16  # black
        if gray > 248:
            return 231  # white
        return 232 + int((gray - 8) / 10)

    # 6x6x6 color cube: 16 + 36*r_idx + 6*g_idx + b_idx
    # where indices are in range [0, 5]
    r_idx = int(round(r / 255.0 * 5.0))
    g_idx = int(round(g / 255.0 * 5.0))
    b_idx = int(round(b / 255.0 * 5.0))
    return 16 + 36 * r_idx + 6 * g_idx + b_idx


def map_colors_to_palette(
    rgb_grid: np.ndarray,
    luminance: np.ndarray,
    style: str,
    foreground_hex: str = "#FFFFFF",
) -> np.ndarray:
    """Generate the effective RGB display colors for each cell based on style.

    Args:
        rgb_grid: Downsampled RGB frame of shape (H, W, 3), uint8.
        luminance: 2D float array in [0.0, 1.0].
        style: 'color', 'monochrome', 'green', 'amber', or 'custom'.
        foreground_hex: Target foreground color for monochrome/custom.

    Returns:
        Numpy array of shape (H, W, 3) uint8 containing final cell colors.
    """
    h, w = luminance.shape

    if style == "color":
        return rgb_grid

    lum_expanded = luminance[..., np.newaxis]  # shape (H, W, 1)

    if style == "green":
        # Green phosphor: bright green #33FF33 scaled by luminance
        base_green = np.array([0x33, 0xFF, 0x33], dtype=np.float32)
        out = lum_expanded * base_green
        return np.clip(out, 0, 255).astype(np.uint8)

    if style == "amber":
        # Amber phosphor: #FFB000 scaled by luminance
        base_amber = np.array([0xFF, 0xB0, 0x00], dtype=np.float32)
        out = lum_expanded * base_amber
        return np.clip(out, 0, 255).astype(np.uint8)

    if style in ("monochrome", "custom"):
        fg_r, fg_g, fg_b = hex_to_rgb(foreground_hex)
        base_fg = np.array([fg_r, fg_g, fg_b], dtype=np.float32)
        out = lum_expanded * base_fg
        return np.clip(out, 0, 255).astype(np.uint8)

    return rgb_grid


def format_ansi_truecolor(r: int, g: int, b: int) -> str:
    """ANSI 24-bit foreground escape sequence."""
    return f"\033[38;2;{r};{g};{b}m"


def format_ansi_bg_truecolor(r: int, g: int, b: int) -> str:
    """ANSI 24-bit background escape sequence."""
    return f"\033[48;2;{r};{g};{b}m"


ANSI_RESET = "\033[0m"
