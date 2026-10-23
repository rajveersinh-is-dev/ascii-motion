"""Plain text and ANSI sequence exporters."""

from __future__ import annotations

from pathlib import Path

from ascii_motion.core.converter import AsciiFrame


def export_to_text(
    frames: list[AsciiFrame],
    output_path: str | Path,
    include_ansi: bool = False,
    background_hex: str | None = None,
) -> Path:
    """Export ASCII frame(s) to a .txt or .ans file.

    If multiple frames are passed, separates them with a form-feed delimiter (`\\x0c`).

    Args:
        frames: List of AsciiFrame instances.
        output_path: Target file path.
        include_ansi: If True, formats with 24-bit ANSI color escape codes.
        background_hex: Optional background hex color.

    Returns:
        Path to output file.
    """
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    parts: list[str] = []
    for frame in frames:
        if include_ansi:
            parts.append(frame.to_ansi(background_hex=background_hex))
        else:
            parts.append(frame.to_text())

    # Form-feed separator for multi-frame text sequences
    content = "\n\x0c\n".join(parts) + "\n"
    out_file.write_text(content, encoding="utf-8")
    return out_file
