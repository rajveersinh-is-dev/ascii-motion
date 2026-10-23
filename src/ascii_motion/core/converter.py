"""High-performance frame-to-ASCII conversion engine."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image

from ascii_motion.config import RenderConfig
from ascii_motion.core.color import (
    ANSI_RESET,
    format_ansi_bg_truecolor,
    format_ansi_truecolor,
    hex_to_rgb,
    map_colors_to_palette,
)
from ascii_motion.core.dithering import apply_bayer_dithering, apply_floyd_steinberg_dithering
from ascii_motion.core.edge import (
    compute_sobel_gradients,
    enhance_edges,
    get_directional_edge_chars,
)
from ascii_motion.core.perceptual import (
    adjust_tone,
    apply_temporal_smoothing,
    rgb_to_luminance,
)
from ascii_motion.core.ramps import get_ramp


@dataclass(slots=True)
class AsciiFrame:
    """Rendered ASCII frame representation."""

    chars: np.ndarray  # 2D array of shape (H, W) dtype '<U1'
    colors: np.ndarray  # 3D array of shape (H, W, 3) dtype uint8
    width: int
    height: int
    frame_index: int = 0
    timestamp: float = 0.0

    def to_text(self) -> str:
        """Convert character grid to plain multi-line string."""
        return "\n".join("".join(row) for row in self.chars)

    def to_ansi(self, background_hex: str | None = None) -> str:
        """Serialize frame to ANSI truecolor escape string with optional background."""
        lines: list[str] = []
        bg_code = ""
        if background_hex is not None:
            bg_r, bg_g, bg_b = hex_to_rgb(background_hex)
            bg_code = format_ansi_bg_truecolor(bg_r, bg_g, bg_b)

        last_r, last_g, last_b = -1, -1, -1
        current_fg_code = ""

        for y in range(self.height):
            row_chars = self.chars[y]
            row_colors = self.colors[y]
            line_parts: list[str] = [bg_code] if bg_code else []

            for x in range(self.width):
                r, g, b = int(row_colors[x, 0]), int(row_colors[x, 1]), int(row_colors[x, 2])
                if (r, g, b) != (last_r, last_g, last_b):
                    current_fg_code = format_ansi_truecolor(r, g, b)
                    last_r, last_g, last_b = r, g, b
                line_parts.append(current_fg_code)
                line_parts.append(str(row_chars[x]))

            lines.append("".join(line_parts))

        return "\n".join(lines) + ANSI_RESET


class FrameConverter:
    """Stateful, optimized frame converter supporting temporal smoothing and vectorization."""

    def __init__(self, config: RenderConfig) -> None:
        self.config = config
        self.ramp = get_ramp(
            name=config.ramp_name,
            custom=config.custom_ramp,
            invert=config.invert,
        )
        self.ramp_arr = np.array(list(self.ramp), dtype="<U1")
        self.ramp_len = len(self.ramp)
        self.prev_luminance: np.ndarray | None = None

    def calculate_dimensions(self, src_width: int, src_height: int) -> tuple[int, int]:
        """Compute target (width, height) preserving aspect ratio with character geometry."""
        target_w = self.config.width
        if self.config.height is not None:
            return target_w, self.config.height

        src_aspect = max(src_width, 1) / max(src_height, 1)
        # Monospace character cells are typically ~2x taller than wide
        # Height = width / (src_aspect) * char_aspect_ratio
        target_h = int(round((target_w / src_aspect) * self.config.char_aspect_ratio))
        return target_w, max(1, target_h)

    def reset_state(self) -> None:
        """Reset temporal smoothing state."""
        self.prev_luminance = None

    def convert_frame(
        self,
        frame: np.ndarray | Image.Image,
        frame_index: int = 0,
        timestamp: float = 0.0,
    ) -> AsciiFrame:
        """Convert a single video frame into an AsciiFrame.

        Args:
            frame: Input RGB frame as uint8 numpy array (H, W, 3) or PIL Image.
            frame_index: Sequential index of the frame.
            timestamp: Presentation timestamp in seconds.

        Returns:
            Rendered AsciiFrame instance.
        """
        if isinstance(frame, np.ndarray):
            src_h, src_w = frame.shape[:2]
            pil_img = Image.fromarray(frame)
        else:
            src_w, src_h = frame.size
            pil_img = frame

        target_w, target_h = self.calculate_dimensions(src_w, src_h)

        # 1. Downsample image to character resolution
        # Resampling.BILINEAR balances quality and speed
        resized_img = pil_img.resize((target_w, target_h), resample=Image.Resampling.BILINEAR)
        resized_rgb = np.array(resized_img, dtype=np.uint8)

        # Ensure 3-channel RGB
        if resized_rgb.ndim == 2:
            resized_rgb = np.stack([resized_rgb] * 3, axis=-1)
        elif resized_rgb.shape[2] > 3:
            resized_rgb = resized_rgb[:, :, :3]

        # 2. Perceptual luminance calculation (BT.709)
        lum = rgb_to_luminance(resized_rgb, standard="bt709")

        # 3. Tone mapping (brightness, contrast, gamma, invert)
        lum = adjust_tone(
            lum,
            brightness=self.config.brightness,
            contrast=self.config.contrast,
            gamma=self.config.gamma,
            invert=self.config.invert,
        )

        # 4. Temporal stabilization
        if self.config.temporal_smoothing > 0.0:
            lum = apply_temporal_smoothing(
                lum,
                self.prev_luminance,
                alpha=self.config.temporal_smoothing,
            )
            self.prev_luminance = np.copy(lum)

        # 5. Edge enhancement
        gx, gy, mag = None, None, None
        if self.config.edge_mode == "sobel":
            mag, gx, gy = compute_sobel_gradients(lum)
            lum = enhance_edges(lum, strength=self.config.edge_strength)

        # 6. Dithering
        if self.config.dithering == "bayer":
            lum = apply_bayer_dithering(lum, num_levels=self.ramp_len)
        elif self.config.dithering == "floyd_steinberg":
            lum = apply_floyd_steinberg_dithering(lum, num_levels=self.ramp_len)

        # 7. Vectorized character mapping
        indices = np.clip(
            np.round(lum * (self.ramp_len - 1)).astype(np.int32),
            0,
            self.ramp_len - 1,
        )
        chars = self.ramp_arr[indices]

        # 8. Optional directional edge character injection
        if (
            self.config.edge_mode == "sobel"
            and gx is not None
            and gy is not None
            and mag is not None
        ):
            dir_chars = get_directional_edge_chars(gx, gy, mag, threshold=0.4)
            edge_mask = dir_chars != " "
            chars[edge_mask] = dir_chars[edge_mask]

        # 9. Colors mapping
        final_colors = map_colors_to_palette(
            resized_rgb,
            luminance=lum,
            style=self.config.style,
            foreground_hex=self.config.foreground_color,
        )

        return AsciiFrame(
            chars=chars,
            colors=final_colors,
            width=target_w,
            height=target_h,
            frame_index=frame_index,
            timestamp=timestamp,
        )
