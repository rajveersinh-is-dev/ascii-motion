"""Animated GIF exporter for ASCII animations."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageFont

from ascii_motion.config import RenderConfig
from ascii_motion.core.converter import AsciiFrame
from ascii_motion.exporters.mp4 import render_ascii_frame_to_image


def export_to_gif(
    frames: list[AsciiFrame],
    config: RenderConfig,
    output_path: str | Path,
    fps: float | None = None,
) -> Path:
    """Render ASCII frames to an optimized animated GIF file.

    Args:
        frames: List of AsciiFrame instances.
        config: RenderConfig used.
        output_path: Target .gif file path.
        fps: Target frame rate.

    Returns:
        Path to output GIF file.
    """
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    if not frames:
        raise ValueError("Cannot export GIF with zero frames.")

    target_fps = fps or config.target_fps or 15.0
    duration_ms = int(round(1000.0 / target_fps))

    font = ImageFont.load_default()
    bbox = font.getbbox("M")
    char_w = max(bbox[2] - bbox[0], 6)
    char_h = max(bbox[3] - bbox[1], 12)

    pil_images: list[Image.Image] = []
    for frame in frames:
        rgb_arr = render_ascii_frame_to_image(frame, config, char_w, char_h, font)
        # Convert RGB to P (quantized palette) with adaptive palette for compact GIF
        frame_img = Image.fromarray(rgb_arr).convert(
            "P", palette=Image.Palette.ADAPTIVE, colors=256
        )
        pil_images.append(frame_img)

    pil_images[0].save(
        out_file,
        save_all=True,
        append_images=pil_images[1:],
        duration=duration_ms,
        loop=0,
        optimize=True,
    )

    return out_file
