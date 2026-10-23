"""Generate reproducible demonstration assets for README and repository."""

from pathlib import Path

from ascii_motion.config import RenderConfig
from ascii_motion.core.converter import FrameConverter
from ascii_motion.exporters.gif import export_to_gif
from ascii_motion.exporters.html import export_to_html
from ascii_motion.exporters.mp4 import export_to_mp4
from ascii_motion.utils.synthetic import create_synthetic_video
from ascii_motion.video.probe import probe_video
from ascii_motion.video.reader import VideoStreamReader


def main() -> None:
    assets_dir = Path.cwd() / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    source_path = assets_dir / "demo_source.mp4"
    print(f"1. Generating deterministic synthetic source video -> {source_path.name}...")
    create_synthetic_video(
        output_path=source_path,
        duration=2.5,
        fps=20.0,
        width=640,
        height=360,
        include_audio=True,
    )
    print(f"   Created source: {source_path.stat().st_size / 1024:.1f} KB")

    config = RenderConfig(
        preset="custom",
        width=120,
        ramp_name="standard_70",
        style="color",
        target_fps=15.0,
        dithering="bayer",
        edge_mode="sobel",
        contrast=1.2,
        brightness=1.1,
    )
    meta = probe_video(source_path)
    converter = FrameConverter(config)

    print("2. Converting frames through ascii-motion core engine...")
    frames = []
    with VideoStreamReader(source_path, config, meta) as reader:
        for idx, ts, raw_arr in reader.frames():
            frames.append(converter.convert_frame(raw_arr, idx, ts))
    print(f"   Converted {len(frames)} frames ({frames[0].width}x{frames[0].height} grid).")

    # 3. Export animated GIF for README embedding
    gif_path = assets_dir / "demo_animated.gif"
    print(f"3. Exporting animated GIF -> {gif_path.name}...")
    export_to_gif(frames, config, gif_path, fps=15.0)
    print(f"   Created GIF: {gif_path.stat().st_size / 1024:.1f} KB")

    # 4. Export standalone offline HTML player
    html_path = assets_dir / "demo_player.html"
    print(f"4. Exporting standalone HTML player -> {html_path.name}...")
    export_to_html(frames, config, html_path, title="ascii-motion Interactive Demo")
    print(f"   Created HTML: {html_path.stat().st_size / 1024:.1f} KB")

    # 5. Export rendered MP4 video
    mp4_path = assets_dir / "demo_output.mp4"
    print(f"5. Exporting rendered MP4 video -> {mp4_path.name}...")
    export_to_mp4(frames, config, mp4_path, source_video=source_path, fps=15.0)
    print(f"   Created MP4: {mp4_path.stat().st_size / 1024:.1f} KB")

    print("\nDemonstration assets successfully generated!")


if __name__ == "__main__":
    main()
