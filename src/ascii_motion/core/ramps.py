"""Character ramps and dynamic glyph density measurement."""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFont

PREDEFINED_RAMPS: dict[str, str] = {
    # Ordered from lowest visual density (darkest) to highest visual density (brightest)
    "standard_10": " .:-=+*#%@",
    "standard_16": " .'`^,:;Il!i~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",
    "standard_70": (" .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"),
    "blocks": " ░▒▓█",
    "minimal": " .#",
    "binary": " 01",
    "matrix": " .:=*#ｦｱｳｴｵｶｷｹｺｻｼｽｾｿﾀﾂﾃﾅﾆﾇﾈﾊﾋﾎﾏﾐﾑﾒﾓﾔﾕﾗﾘﾜ",
}


def get_ramp(name: str = "standard_10", custom: str | None = None, invert: bool = False) -> str:
    """Retrieve and optionally invert a character ramp.

    Args:
        name: Name of predefined ramp.
        custom: Optional user-provided custom ramp string.
        invert: If True, reverses the character ramp.

    Returns:
        The validated character ramp string.
    """
    if custom and len(set(custom)) >= 2:
        ramp = custom
    elif name in PREDEFINED_RAMPS:
        ramp = PREDEFINED_RAMPS[name]
    else:
        ramp = PREDEFINED_RAMPS["standard_10"]

    if invert:
        ramp = ramp[::-1]

    return ramp


def measure_glyph_densities(
    chars: str,
    cell_width: int = 16,
    cell_height: int = 24,
) -> list[tuple[str, float]]:
    """Measure the actual visual density (fill ratio) of characters by rendering them.

    Renders each character into a monochrome bitmap using Pillow and calculates
    the fraction of filled pixels over total cell area.

    Args:
        chars: String of characters to evaluate.
        cell_width: Width of the render cell in pixels.
        cell_height: Height of the render cell in pixels.

    Returns:
        A list of (character, fill_ratio) tuples sorted from lowest to highest density.
    """
    unique_chars = sorted(set(chars))
    results: list[tuple[str, float]] = []

    # Try default load font or fallback to basic bitmap
    font = ImageFont.load_default()

    for ch in unique_chars:
        if ch == " " or ch == "\t":
            results.append((ch, 0.0))
            continue

        # Render glyph onto black background
        img = Image.new("L", (cell_width, cell_height), color=0)
        draw = ImageDraw.Draw(img)
        draw.text((2, 2), ch, fill=255, font=font)

        arr = np.array(img, dtype=np.float32)
        # Proportion of non-black pixels
        density = float(np.count_nonzero(arr > 0) / arr.size)
        results.append((ch, density))

    results.sort(key=lambda item: item[1])
    return results


def build_calibrated_ramp(chars: str) -> str:
    """Construct an empirically ordered character ramp from any character set.

    Measures the rendered glyph densities from first principles and arranges
    the characters in ascending order of visual weight.

    Args:
        chars: Input characters.

    Returns:
        Ascending density ramp string.
    """
    measured = measure_glyph_densities(chars)
    # Deduplicate while preserving density order
    ordered_chars: list[str] = []
    seen: set[str] = set()
    for ch, _ in measured:
        if ch not in seen:
            seen.add(ch)
            ordered_chars.append(ch)

    return "".join(ordered_chars)
