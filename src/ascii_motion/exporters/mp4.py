"""MP4 video exporter rendering ASCII characters to video frames."""

from __future__ import annotations

import subprocess
from collections.abc import Iterable
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ascii_motion.config import RenderConfig
from ascii_motion.core.color import hex_to_rgb
from ascii_motion.core.converter import AsciiFrame
from ascii_motion.video.ffmpeg import get_ffmpeg_path
from ascii_motion.video.probe import probe_video


def get_monospace_font(size: int = 16) -> tuple[ImageFont.ImageFont, int, int]:
    """Find and load a crisp monospace font, returning (font, char_width, char_height)."""
    candidates = [
        "C:/Windows/Fonts/consolab.ttf",
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/courbd.ttf",
        "C:/Windows/Fonts/cour.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/Library/Fonts/Courier New Bold.ttf",
    ]
    font: ImageFont.ImageFont | None = None
    for cand in candidates:
        if Path(cand).is_file():
            try:
                font = ImageFont.truetype(cand, size=size)
                break
            except Exception:
                pass

    if font is None:
        try:
            font = ImageFont.load_default(size=size)
        except TypeError:
            font = ImageFont.load_default()

    bbox = font.getbbox("M")
    adv = font.getlength("M") if hasattr(font, "getlength") else float(bbox[2] - bbox[0])
    char_w = max(int(round(adv)), 8)
    char_h = max(int(round(char_w / 0.55)), 14)
    return font, char_w, char_h


def render_ascii_frame_to_image(
    frame: AsciiFrame,
    config: RenderConfig,
    char_w: int,
    char_h: int,
    font: ImageFont.ImageFont,
) -> np.ndarray:
    """Render an AsciiFrame to an RGB raster image numpy array.

    Optimized by drawing entire strings when colors are uniform, or grouping
    consecutive characters sharing the same color.
    """
    canvas_w = frame.width * char_w
    canvas_h = frame.height * char_h
    bg_rgb = hex_to_rgb(config.background_color)

    img = Image.new("RGB", (canvas_w, canvas_h), color=bg_rgb)
    draw = ImageDraw.Draw(img)

    is_color = config.style == "color"

    if not is_color:
        # Uniform color style (monochrome, green, amber, custom)
        fg_rgb = (255, 255, 255)
        if config.style == "green":
            fg_rgb = (0x33, 0xFF, 0x33)
        elif config.style == "amber":
            fg_rgb = (0xFF, 0xB0, 0x00)
        elif config.style in ("monochrome", "custom"):
            fg_rgb = hex_to_rgb(config.foreground_color)

        for y in range(frame.height):
            line = "".join(frame.chars[y])
            draw.text((0, y * char_h), line, fill=fg_rgb, font=font)
    else:
        # Truecolor: group contiguous characters with identical RGB to minimize draw calls
        for y in range(frame.height):
            y_pos = y * char_h
            row_chars = frame.chars[y]
            row_colors = frame.colors[y]

            x = 0
            while x < frame.width:
                cur_color = (
                    int(row_colors[x, 0]),
                    int(row_colors[x, 1]),
                    int(row_colors[x, 2]),
                )
                start_x = x
                run_chars: list[str] = [str(row_chars[x])]
                x += 1
                while x < frame.width:
                    next_color = (
                        int(row_colors[x, 0]),
                        int(row_colors[x, 1]),
                        int(row_colors[x, 2]),
                    )
                    if next_color == cur_color:
                        run_chars.append(str(row_chars[x]))
                        x += 1
                    else:
                        break

                text_run = "".join(run_chars)
                draw.text((start_x * char_w, y_pos), text_run, fill=cur_color, font=font)

    return np.array(img, dtype=np.uint8)


def export_to_mp4(
    frames: Iterable[AsciiFrame],
    config: RenderConfig,
    output_path: str | Path,
    source_video: str | Path | None = None,
    include_audio: bool = True,
    fps: float | None = None,
) -> Path:
    """Render ASCII frames to a readable MP4 video file via FFmpeg.

    Args:
        frames: Iterable of AsciiFrame instances.
        config: RenderConfig used.
        output_path: Target .mp4 file path.
        source_video: Optional path to source video for audio passthrough.
        include_audio: Whether to preserve/sync audio from source_video if present.
        fps: Target frame rate (defaults to config.target_fps or 24.0).

    Returns:
        Path to completed MP4 file.
    """
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    target_fps = fps or config.target_fps or 24.0
    ffmpeg_exe = get_ffmpeg_path()

    font, char_w, char_h = get_monospace_font(size=15)

    # Convert frames iterator to list if needed for dimensions
    frames_list = list(frames)
    if not frames_list:
        raise ValueError("Cannot export MP4 video with zero frames.")

    sample_frame = frames_list[0]
    canvas_w = sample_frame.width * char_w
    canvas_h = sample_frame.height * char_h

    # Ensure even canvas dimensions for H.264
    if canvas_w % 2 != 0:
        canvas_w += 1
    if canvas_h % 2 != 0:
        canvas_h += 1

    cmd: list[str] = [
        ffmpeg_exe,
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{canvas_w}x{canvas_h}",
        "-r",
        f"{target_fps:.3f}",
        "-i",
        "-",
    ]

    has_audio_input = False
    if source_video and include_audio:
        src_path = Path(source_video).resolve()
        if src_path.is_file():
            try:
                meta = probe_video(src_path)
                if meta.has_audio:
                    has_audio_input = True
                    if config.trim_start > 0:
                        cmd.extend(["-ss", f"{config.trim_start:.3f}"])
                    cmd.extend(["-i", str(src_path)])
            except Exception:
                has_audio_input = False

    if has_audio_input:
        cmd.extend(["-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-b:a", "128k", "-shortest"])
    else:
        cmd.extend(["-map", "0:v:0"])

    cmd.extend(
        [
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "fast",
            "-crf",
            "20",
            str(out_file),
        ]
    )

    import tempfile

    with tempfile.TemporaryFile() as stderr_file:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=stderr_file,
        )

        try:
            assert process.stdin is not None
            for frame in frames_list:
                if process.poll() is not None:
                    break
                frame_img = render_ascii_frame_to_image(frame, config, char_w, char_h, font)
                # Resize if padding needed for even dimensions
                if frame_img.shape[1] != canvas_w or frame_img.shape[0] != canvas_h:
                    padded = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)
                    h = min(frame_img.shape[0], canvas_h)
                    w = min(frame_img.shape[1], canvas_w)
                    padded[:h, :w] = frame_img[:h, :w]
                    data_to_write = padded.tobytes()
                else:
                    data_to_write = frame_img.tobytes()

                try:
                    process.stdin.write(data_to_write)
                except (BrokenPipeError, OSError):
                    break

            try:
                process.stdin.close()
            except (BrokenPipeError, OSError):
                pass
            process.wait(timeout=120.0)
        except Exception as exc:
            stderr_file.seek(0)
            err_details = stderr_file.read().decode("utf-8", errors="replace")
            if out_file.is_file():
                try:
                    out_file.unlink()
                except OSError:
                    pass
            raise RuntimeError(f"MP4 export error: {exc}. FFmpeg log:\n{err_details}") from exc

        if process.returncode != 0:
            if out_file.is_file():
                try:
                    out_file.unlink()
                except OSError:
                    pass
            stderr_file.seek(0)
            err_msg = stderr_file.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"FFmpeg MP4 encoding failed (exit code {process.returncode}): {err_msg}"
            )

    return out_file
