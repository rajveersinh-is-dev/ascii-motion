"""Programmatic generation of deterministic synthetic test videos."""

from __future__ import annotations

import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ascii_motion.video.ffmpeg import get_ffmpeg_path


def generate_synthetic_frame(
    frame_idx: int,
    total_frames: int,
    width: int = 640,
    height: int = 360,
) -> np.ndarray:
    """Generate a single deterministic synthetic RGB video frame.

    Draws a vibrant scene with rotating 3D wireframe cube, bouncing sphere,
    pulsing concentric rings, animated high-contrast gradients, and readable text.
    """
    img = Image.new("RGB", (width, height), color=(10, 12, 20))
    draw = ImageDraw.Draw(img)

    t = frame_idx / max(total_frames, 1)  # Normalized time [0, 1]
    angle = 2.0 * math.pi * t

    # 1. Background radial gradient / pulsing glow
    cx, cy = width // 2, height // 2
    pulse_radius = int(80 + 30 * math.sin(angle * 2))
    for r in range(pulse_radius, 0, -10):
        intensity = int(40 * (1.0 - r / pulse_radius))
        draw.ellipse(
            [cx - r * 2, cy - r, cx + r * 2, cy + r],
            outline=(intensity // 2, intensity, intensity * 2),
        )

    # 2. Pulsing concentric circular rings
    num_rings = 4
    for i in range(num_rings):
        ring_phase = (t + i / num_rings) % 1.0
        r_rad = int(ring_phase * min(width, height) * 0.45)
        alpha = int(255 * (1.0 - ring_phase))
        color = (
            int(50 + 150 * math.sin(angle + i)),
            int(100 + 100 * math.cos(angle + i * 0.5)),
            alpha,
        )
        draw.ellipse([cx - r_rad, cy - r_rad, cx + r_rad, cy + r_rad], outline=color, width=2)

    # 3. Rotating 3D Wireframe Cube
    cube_nodes = np.array(
        [
            [-1, -1, -1],
            [1, -1, -1],
            [1, 1, -1],
            [-1, 1, -1],
            [-1, -1, 1],
            [1, -1, 1],
            [1, 1, 1],
            [-1, 1, 1],
        ],
        dtype=np.float32,
    )

    rot_y = np.array(
        [
            [math.cos(angle), 0, math.sin(angle)],
            [0, 1, 0],
            [-math.sin(angle), 0, math.cos(angle)],
        ],
        dtype=np.float32,
    )

    rot_x = np.array(
        [
            [1, 0, 0],
            [0, math.cos(angle * 0.7), -math.sin(angle * 0.7)],
            [0, math.sin(angle * 0.7), math.cos(angle * 0.7)],
        ],
        dtype=np.float32,
    )

    rotated = cube_nodes @ rot_y.T @ rot_x.T

    scale = min(width, height) * 0.22
    focal = 3.0
    projected = []
    for node in rotated:
        z = node[2] + focal
        px = int(cx + (node[0] / z) * scale * 2.0)
        py = int(cy + (node[1] / z) * scale * 2.0)
        projected.append((px, py))

    edges = [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 0),  # back face
        (4, 5),
        (5, 6),
        (6, 7),
        (7, 4),  # front face
        (0, 4),
        (1, 5),
        (2, 6),
        (3, 7),  # connecting edges
    ]

    for p1_idx, p2_idx in edges:
        p1 = projected[p1_idx]
        p2 = projected[p2_idx]
        draw.line([p1, p2], fill=(0, 255, 200), width=3)

    # 4. Bouncing high-contrast gradient sphere
    sphere_x = int(cx + math.sin(angle * 2) * (width * 0.35))
    sphere_y = int(cy + abs(math.cos(angle * 2)) * (height * 0.3) - height * 0.15)
    sphere_radius = 28
    draw.ellipse(
        [
            sphere_x - sphere_radius,
            sphere_y - sphere_radius,
            sphere_x + sphere_radius,
            sphere_y + sphere_radius,
        ],
        fill=(255, 60, 120),
        outline=(255, 255, 255),
        width=2,
    )

    # 5. Crisp typography: "ASCII-MOTION"
    font = ImageFont.load_default()
    title = "ASCII-MOTION"
    draw.text((cx - 38, cy - 6), title, fill=(255, 255, 255), font=font)

    # 6. Timecode and progress indicator
    time_str = f"FRAME {frame_idx:03d}/{total_frames:03d} | T={t * 100:.0f}%"
    draw.text((15, height - 25), time_str, fill=(180, 220, 255), font=font)

    # Progress bar at bottom
    bar_width = int(width * t)
    draw.rectangle([0, height - 5, bar_width, height], fill=(0, 255, 128))

    return np.array(img, dtype=np.uint8)


def create_synthetic_audio(
    duration: float,
    sample_rate: int = 44100,
) -> np.ndarray:
    """Synthesize a pleasant harmonic chord (C major triad: 261.63Hz, 329.63Hz, 392.00Hz)."""
    num_samples = int(duration * sample_rate)
    t = np.linspace(0.0, duration, num_samples, endpoint=False)

    wave = (
        0.4 * np.sin(2.0 * np.pi * 261.63 * t)
        + 0.3 * np.sin(2.0 * np.pi * 329.63 * t)
        + 0.3 * np.sin(2.0 * np.pi * 392.00 * t)
    )

    envelope = np.ones_like(wave)
    fade_len = int(sample_rate * 0.2)
    if fade_len > 0 and len(wave) > 2 * fade_len:
        envelope[:fade_len] = np.linspace(0, 1, fade_len)
        envelope[-fade_len:] = np.linspace(1, 0, fade_len)

    wave = (wave * envelope * 0.7 * 32767).astype(np.int16)
    return wave


def create_synthetic_video(
    output_path: str | Path,
    duration: float = 3.0,
    fps: float = 30.0,
    width: int = 640,
    height: int = 360,
    include_audio: bool = True,
) -> Path:
    """Generate and encode a complete synthetic test video file."""
    out_path = Path(output_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    ffmpeg_exe = get_ffmpeg_path()
    total_frames = int(round(duration * fps))

    cmd = [
        ffmpeg_exe,
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{width}x{height}",
        "-r",
        f"{fps}",
        "-i",
        "-",
    ]

    temp_wav = out_path.with_suffix(".audio.wav")
    if include_audio:
        sample_rate = 44100
        audio_data = create_synthetic_audio(duration, sample_rate)
        import wave

        with wave.open(str(temp_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data.tobytes())

        cmd.extend(["-i", str(temp_wav), "-c:a", "aac", "-b:a", "128k"])

    cmd.extend(
        [
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "fast",
            "-crf",
            "22",
            str(out_path),
        ]
    )

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    stderr_output = b""
    try:
        assert process.stdin is not None
        for idx in range(total_frames):
            frame_arr = generate_synthetic_frame(idx, total_frames, width, height)
            process.stdin.write(frame_arr.tobytes())
        process.stdin.close()
        _, stderr_output = process.communicate(timeout=30.0)
    finally:
        if temp_wav.is_file():
            try:
                temp_wav.unlink()
            except OSError:
                pass

    if process.returncode != 0:
        err = stderr_output.decode("utf-8", errors="replace") if stderr_output else "Unknown error"
        raise RuntimeError(f"FFmpeg synthetic video encoding failed: {err}")

    return out_path
