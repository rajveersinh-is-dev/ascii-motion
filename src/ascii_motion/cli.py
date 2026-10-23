"""Command-line interface for ascii-motion."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from ascii_motion.config import PRESET_WIDTHS, RenderConfig
from ascii_motion.core.converter import FrameConverter
from ascii_motion.exporters.gif import export_to_gif
from ascii_motion.exporters.html import export_to_html
from ascii_motion.exporters.mp4 import export_to_mp4
from ascii_motion.exporters.terminal import play_in_terminal
from ascii_motion.exporters.text import export_to_text
from ascii_motion.video.probe import probe_video
from ascii_motion.video.reader import VideoStreamReader


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="ascii-motion",
        description="Convert ordinary video into animated ASCII representations with high visual fidelity.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # Live terminal playback
  ascii-motion input.mp4 --mode terminal --width 100

  # Render colored ASCII MP4 video
  ascii-motion input.mp4 --output output.mp4 --preset medium --style color

  # Generate standalone offline HTML player
  ascii-motion input.mp4 --output animation.html --preset high --style green

  # Export animated GIF with custom ramp
  ascii-motion input.mp4 --output demo.gif --ramp blocks --fps 15
""",
    )

    parser.add_argument("input", nargs="?", help="Path to input video file")
    parser.add_argument("-o", "--output", help="Output file path (.mp4, .html, .gif, .txt, .ans)")
    parser.add_argument(
        "-m",
        "--mode",
        choices=["terminal", "export"],
        default=None,
        help="Execution mode: 'terminal' for live playback, 'export' to save file (default inferred from --output)",
    )

    # Resolution & geometry
    res_group = parser.add_argument_group("Resolution & Geometry")
    res_group.add_argument(
        "-p",
        "--preset",
        choices=["low", "medium", "high", "ultra", "custom"],
        default="medium",
        help="Resolution preset: low (60 cols), medium (100), high (160), ultra (240)",
    )
    res_group.add_argument(
        "-w", "--width", type=int, default=None, help="Target character width (columns)"
    )
    res_group.add_argument(
        "--height", type=int, default=None, help="Target character height (rows, None=auto)"
    )
    res_group.add_argument(
        "--char-aspect", type=float, default=0.5, help="Character cell aspect ratio (default 0.5)"
    )

    # Visual style & tone
    style_group = parser.add_argument_group("Visual Style & Tone Mapping")
    style_group.add_argument(
        "-s",
        "--style",
        choices=["monochrome", "color", "green", "amber", "custom"],
        default="color",
        help="Color style (default: color)",
    )
    style_group.add_argument(
        "--fg", "--foreground", default="#FFFFFF", help="Foreground color (hex)"
    )
    style_group.add_argument(
        "--bg", "--background", default="#000000", help="Background color (hex)"
    )
    style_group.add_argument(
        "-r",
        "--ramp",
        default="standard_10",
        help="Character ramp preset name (standard_10, standard_16, standard_70, blocks, minimal, binary, matrix)",
    )
    style_group.add_argument("--custom-ramp", default=None, help="Explicit character ramp string")
    style_group.add_argument(
        "--brightness", type=float, default=1.0, help="Brightness multiplier (default 1.0)"
    )
    style_group.add_argument(
        "--contrast", type=float, default=1.0, help="Contrast multiplier (default 1.0)"
    )
    style_group.add_argument(
        "--gamma", type=float, default=1.0, help="Gamma exponent (default 1.0)"
    )
    style_group.add_argument("--invert", action="store_true", help="Invert luminance mapping")

    # Advanced quality
    adv_group = parser.add_argument_group("Advanced Quality Features")
    adv_group.add_argument(
        "--dither",
        choices=["none", "bayer", "floyd_steinberg"],
        default="none",
        help="Dithering method",
    )
    adv_group.add_argument(
        "--edge", choices=["none", "sobel"], default="none", help="Edge enhancement mode"
    )
    adv_group.add_argument(
        "--edge-strength", type=float, default=0.5, help="Edge enhancement strength"
    )
    adv_group.add_argument(
        "--temporal-smoothing",
        type=float,
        default=0.0,
        help="Temporal stabilization factor (0.0 to 0.9)",
    )

    # Timing & limits
    timing_group = parser.add_argument_group("Timing & Trimming")
    timing_group.add_argument(
        "--fps", type=float, default=None, help="Target FPS sampling (default: source FPS)"
    )
    timing_group.add_argument(
        "--trim-start", type=float, default=0.0, help="Start trim offset in seconds"
    )
    timing_group.add_argument(
        "--trim-end", type=float, default=None, help="End trim offset in seconds"
    )
    timing_group.add_argument(
        "--max-duration", type=float, default=None, help="Max duration in seconds"
    )
    timing_group.add_argument(
        "--max-frames", type=int, default=None, help="Maximum number of frames to render"
    )
    timing_group.add_argument(
        "--no-audio", action="store_true", help="Disable audio preservation in MP4 export"
    )
    timing_group.add_argument("--loop", action="store_true", help="Loop playback in terminal mode")

    # Config & Reporting
    config_group = parser.add_argument_group("Configuration & Reports")
    config_group.add_argument("-c", "--config", help="Load settings from a JSON configuration file")
    config_group.add_argument(
        "--save-config", help="Save resolved configuration to a JSON file and exit"
    )
    config_group.add_argument(
        "--report", help="Save machine-readable execution report to a JSON file"
    )
    config_group.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress non-error console output"
    )
    config_group.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose diagnostics"
    )

    return parser


def parse_config(args: argparse.Namespace) -> RenderConfig:
    """Build a RenderConfig from parsed CLI arguments and optional config file."""
    config_data: dict[str, Any] = {}

    if args.config:
        cfg_path = Path(args.config).resolve()
        if not cfg_path.is_file():
            raise FileNotFoundError(f"Configuration file not found: {cfg_path}")
        with open(cfg_path, encoding="utf-8") as f:
            config_data = json.load(f)

    # CLI arguments override file configuration
    width = args.width
    preset = args.preset
    if width is not None:
        preset = "custom"
    elif "preset" in config_data:
        preset = config_data["preset"]
        width = PRESET_WIDTHS.get(preset, 100)
    else:
        width = PRESET_WIDTHS.get(preset, 100)

    cfg = RenderConfig(
        preset=preset,
        width=width,
        height=args.height or config_data.get("height"),
        char_aspect_ratio=args.char_aspect or config_data.get("char_aspect_ratio", 0.5),
        target_fps=args.fps or config_data.get("target_fps"),
        trim_start=args.trim_start or config_data.get("trim_start", 0.0),
        trim_end=args.trim_end or config_data.get("trim_end"),
        max_duration=args.max_duration or config_data.get("max_duration"),
        max_frames=args.max_frames or config_data.get("max_frames"),
        brightness=args.brightness or config_data.get("brightness", 1.0),
        contrast=args.contrast or config_data.get("contrast", 1.0),
        gamma=args.gamma or config_data.get("gamma", 1.0),
        invert=args.invert or config_data.get("invert", False),
        ramp_name=args.ramp or config_data.get("ramp_name", "standard_10"),
        custom_ramp=args.custom_ramp or config_data.get("custom_ramp"),
        style=args.style or config_data.get("style", "color"),
        foreground_color=args.fg or config_data.get("foreground_color", "#FFFFFF"),
        background_color=args.bg or config_data.get("background_color", "#000000"),
        dithering=args.dither or config_data.get("dithering", "none"),
        edge_mode=args.edge or config_data.get("edge_mode", "none"),
        edge_strength=args.edge_strength or config_data.get("edge_strength", 0.5),
        temporal_smoothing=args.temporal_smoothing or config_data.get("temporal_smoothing", 0.0),
    )
    return cfg


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.input and not args.save_config:
        parser.print_help()
        return 0

    try:
        config = parse_config(args)
    except Exception as exc:
        sys.stderr.write(f"Configuration error: {exc}\n")
        return 1

    if args.save_config:
        save_path = Path(args.save_config).resolve()
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(config.model_dump_json(indent=2), encoding="utf-8")
        if not args.quiet:
            sys.stdout.write(f"Configuration saved to {save_path}\n")
        return 0

    input_path = Path(args.input).resolve()
    if not input_path.is_file():
        sys.stderr.write(f"Error: Input video file does not exist: {input_path}\n")
        return 1

    try:
        metadata = probe_video(input_path)
    except Exception as exc:
        sys.stderr.write(f"Error probing video: {exc}\n")
        return 1

    # Determine mode
    mode = args.mode
    if mode is None:
        mode = "terminal" if not args.output else "export"

    converter = FrameConverter(config)
    start_time = time.perf_counter()

    if mode == "terminal":
        # Live streaming playback in terminal
        with VideoStreamReader(input_path, config, metadata) as reader:
            frame_gen = (
                converter.convert_frame(raw_arr, f_idx, ts)
                for f_idx, ts, raw_arr in reader.frames()
            )
            fps = config.target_fps or metadata.fps
            play_in_terminal(
                frame_gen,
                fps=fps,
                background_hex=config.background_color if config.style != "color" else None,
                loop=args.loop,
            )
        return 0

    # Export mode: collect frames with progress bar
    output_path = Path(args.output).resolve() if args.output else input_path.with_suffix(".html")
    suffix = output_path.suffix.lower()

    if not args.quiet:
        sys.stdout.write(
            f"Converting '{input_path.name}' -> {config.width}x{config.height or 'auto'} ({config.style})...\n"
        )

    frames = []
    with VideoStreamReader(input_path, config, metadata) as reader:
        for idx, ts, raw_arr in reader.frames():
            frame = converter.convert_frame(raw_arr, idx, ts)
            frames.append(frame)
            if not args.quiet and (idx + 1) % 10 == 0:
                sys.stdout.write(f"\rRendered {idx + 1} frames...")
                sys.stdout.flush()

    if not args.quiet and frames:
        sys.stdout.write(f"\rRendered {len(frames)} frames successfully.\n")

    if not frames:
        sys.stderr.write("Error: No frames were extracted from the input video.\n")
        return 1

    target_fps = config.target_fps or metadata.fps
    if not args.quiet:
        sys.stdout.write(f"Exporting to '{output_path.name}'...\n")

    if suffix in (".mp4", ".mov", ".mkv"):
        export_to_mp4(
            frames,
            config,
            output_path,
            source_video=input_path,
            include_audio=not args.no_audio,
            fps=target_fps,
        )
    elif suffix in (".htm", ".html"):
        export_to_html(frames, config, output_path, title=f"ascii-motion: {input_path.name}")
    elif suffix == ".gif":
        export_to_gif(frames, config, output_path, fps=target_fps)
    elif suffix in (".txt", ".ans"):
        is_ansi = suffix == ".ans" or config.style != "monochrome"
        export_to_text(frames, output_path, include_ansi=is_ansi)
    else:
        # Default fallback to HTML
        export_to_html(frames, config, output_path, title=f"ascii-motion: {input_path.name}")

    elapsed = time.perf_counter() - start_time
    file_size = output_path.stat().st_size if output_path.is_file() else 0
    fps_throughput = len(frames) / max(elapsed, 1e-4)

    if not args.quiet:
        sys.stdout.write(
            f"Complete in {elapsed:.2f}s ({fps_throughput:.1f} fps). Output size: {file_size / 1024:.1f} KB -> {output_path}\n"
        )

    if args.report:
        report_data = {
            "input": str(input_path),
            "output": str(output_path),
            "format": suffix.lstrip("."),
            "frames_processed": len(frames),
            "elapsed_seconds": round(elapsed, 4),
            "throughput_fps": round(fps_throughput, 2),
            "output_size_bytes": file_size,
            "render_dimensions": [frames[0].width, frames[0].height],
            "config": config.model_dump(),
        }
        report_path = Path(args.report).resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
