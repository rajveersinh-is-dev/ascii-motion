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

    Renders a vibrant, high-contrast synthwave scene featuring a rotating 3D
    solid-shaded polyhedron with Lambertian directional lighting, glowing retro
    segmented sun, perspective ground grid in motion, specular bouncing sphere,
    high-contrast title banner, and HUD telemetry.
    """
    img = Image.new("RGB", (width, height), color=(15, 10, 30))
    draw = ImageDraw.Draw(img)

    t = frame_idx / max(total_frames, 1)  # Normalized time [0, 1]
    angle = 2.0 * math.pi * t

    # 1. Sky & Horizon Gradient with Twinkling Starfield
    horizon_y = int(height * 0.58)
    for y in range(horizon_y):
        v = y / horizon_y
        r = int(45 + 180 * (v**1.4))
        g = int(20 + 70 * v)
        b = int(75 + 130 * v)
        draw.line([(0, y), (width, y)], fill=(min(255, r), min(255, g), min(255, b)))

    for s_idx in range(35):
        sx = int((17 + s_idx * 37) % width)
        sy = int((11 + s_idx * 19) % (horizon_y - 25))
        twinkle = 0.5 + 0.5 * math.sin(angle * 3.0 + s_idx * 1.7)
        if twinkle > 0.3:
            s_lum = int(180 + 75 * twinkle)
            draw.point((sx, sy), fill=(s_lum, s_lum, 255))

    # Distant mountain peaks along horizon
    mountain_pts = [(0, horizon_y)]
    for mx in range(0, width + 40, 40):
        h_offset = 32.0 * math.sin(mx * 0.02 + 1.0) + 18.0 * math.sin(mx * 0.05)
        mountain_pts.append((mx, int(horizon_y - abs(h_offset))))
    mountain_pts.append((width, horizon_y))
    draw.polygon(mountain_pts, fill=(45, 20, 65), outline=(255, 60, 160), width=2)

    # Ground Gradient
    for y in range(horizon_y, height):
        v = (y - horizon_y) / (height - horizon_y)
        r = int(60 * (1 - v) + 15)
        g = int(30 * (1 - v) + 20)
        b = int(90 * (1 - v) + 50)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # 2. Glowing retro segmented sun
    sun_cx, sun_cy = width // 2, horizon_y - 12
    sun_r = 75
    for r_s in range(sun_r, 0, -2):
        frac = r_s / sun_r
        c_sun = (255, int(240 * (1 - frac * 0.4)), int(80 * (1 - frac)))
        draw.ellipse([sun_cx - r_s, sun_cy - r_s, sun_cx + r_s, sun_cy + r_s], fill=c_sun)

    # Sun horizontal slice blinds
    for y_blind in range(sun_cy - 10, sun_cy + sun_r, 9):
        draw.rectangle(
            [sun_cx - sun_r - 8, y_blind, sun_cx + sun_r + 8, y_blind + 3], fill=(45, 20, 60)
        )

    # 3. Ground perspective grid
    grid_offset = (t * 40.0) % 40.0
    for i in range(-12, 13):
        x_top = sun_cx + i * 22
        x_bot = sun_cx + i * 115
        draw.line([(x_top, horizon_y), (x_bot, height)], fill=(0, 240, 255), width=2)

    for row_idx in range(7):
        prog = ((row_idx * 15.0 + grid_offset) / 105.0) ** 1.8
        y_pos = int(horizon_y + prog * (height - horizon_y))
        if horizon_y < y_pos < height:
            draw.line([(0, y_pos), (width, y_pos)], fill=(255, 20, 190), width=2)

    # 4. Rotating 3D Solid Shaded 20-Face Regular Icosahedron
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    base_verts = []
    for x in [-1.0, 1.0]:
        for y in [-phi, phi]:
            base_verts.append([x, y, 0.0])
    for y in [-1.0, 1.0]:
        for z in [-phi, phi]:
            base_verts.append([0.0, y, z])
    for z in [-1.0, 1.0]:
        for x in [-phi, phi]:
            base_verts.append([x, 0.0, z])
    base_verts = np.array(base_verts, dtype=np.float32)
    base_verts = base_verts / float(np.linalg.norm(base_verts[0]))

    dist_target = 1.05146
    faces = []
    for i in range(12):
        for j in range(i + 1, 12):
            if abs(float(np.linalg.norm(base_verts[i] - base_verts[j])) - dist_target) < 0.08:
                for k in range(j + 1, 12):
                    if (
                        abs(float(np.linalg.norm(base_verts[i] - base_verts[k])) - dist_target)
                        < 0.08
                        and abs(float(np.linalg.norm(base_verts[j] - base_verts[k])) - dist_target)
                        < 0.08
                    ):
                        faces.append([i, j, k])

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

    rot_verts = base_verts @ rot_y.T @ rot_x.T
    focal = 3.2
    scale = 135
    projected = []
    cube_cy = horizon_y - 20
    for v in rot_verts:
        z = v[2] + focal
        px = int(sun_cx + (v[0] / z) * scale * 2.2)
        py = int(cube_cy + (v[1] / z) * scale * 2.2)
        projected.append((px, py))

    colors_20 = [
        (0, 240, 255),
        (255, 0, 140),
        (0, 255, 120),
        (255, 180, 20),
        (180, 50, 255),
        (255, 255, 40),
        (255, 80, 0),
        (0, 200, 255),
        (255, 0, 200),
        (50, 255, 180),
        (240, 220, 0),
        (150, 0, 255),
        (0, 255, 240),
        (255, 120, 0),
        (0, 255, 70),
        (255, 0, 90),
        (120, 180, 255),
        (255, 200, 50),
        (200, 0, 255),
        (0, 255, 150),
    ]

    face_order = []
    for face_idx, idx_list in enumerate(faces):
        avg_z = float(np.mean([rot_verts[i, 2] for i in idx_list]))
        v0, v1, v2 = rot_verts[idx_list[0]], rot_verts[idx_list[1]], rot_verts[idx_list[2]]
        norm = np.cross(v1 - v0, v2 - v0)
        center_face = (v0 + v1 + v2) / 3.0
        if np.dot(norm, center_face) < 0:
            norm = -norm
        norm_len = float(np.linalg.norm(norm))
        if norm_len > 1e-6:
            norm = norm / norm_len
        face_order.append((avg_z, face_idx, idx_list, colors_20[face_idx % len(colors_20)], norm))

    face_order.sort(key=lambda x: x[0])  # Back to front
    light_dir = np.array([0.5, -0.7, -0.6], dtype=np.float32)
    light_dir = light_dir / float(np.linalg.norm(light_dir))

    for _, _, idx_list, col, norm in face_order:
        if norm[2] < 0.15:  # Facing camera
            poly = [projected[i] for i in idx_list]
            diffuse = max(0.55, float(np.dot(-norm, light_dir)))
            face_col = tuple(min(255, int(c * diffuse)) for c in col)
            draw.polygon(poly, fill=face_col, outline=(255, 255, 255), width=2)

    # 5. Bouncing 3D Shaded Specular Sphere
    sphere_cx = int(sun_cx + math.sin(angle * 2.0) * (width * 0.36))
    bounce_phase = abs(math.cos(angle * 2.0))
    sphere_cy = int(horizon_y + 10 - bounce_phase * (height * 0.35))
    s_rad = 26
    for sr in range(s_rad, 0, -1):
        s_frac = sr / s_rad
        hx = sphere_cx - int(s_rad * 0.35 * (1 - s_frac))
        hy = sphere_cy - int(s_rad * 0.35 * (1 - s_frac))
        scol = (
            min(255, int(255 * (1 - s_frac * 0.6))),
            min(255, int(60 + 195 * (1 - s_frac))),
            min(255, int(120 + 135 * (1 - s_frac))),
        )
        draw.ellipse([hx - sr, hy - sr, hx + sr, hy + sr], fill=scol)
    draw.ellipse(
        [sphere_cx - s_rad, sphere_cy - s_rad, sphere_cx + s_rad, sphere_cy + s_rad],
        outline=(255, 255, 255),
        width=2,
    )

    # 6. Top Title Banner
    banner_w, banner_h = 240, 32
    bx, by = (width - banner_w) // 2, 12
    draw.rectangle(
        [bx, by, bx + banner_w, by + banner_h],
        fill=(10, 15, 30),
        outline=(0, 240, 255),
        width=2,
    )
    font = ImageFont.load_default()
    draw.text((bx + 75, by + 10), "ASCII-MOTION", fill=(255, 255, 255), font=font)

    # 7. Progress indicator
    pbar_w = int(width * t)
    draw.rectangle([0, height - 6, pbar_w, height], fill=(0, 255, 128))

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
        try:
            process.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        stderr_output = process.stderr.read() if process.stderr else b""
        process.wait(timeout=30.0)
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
