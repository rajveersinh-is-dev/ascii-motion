"""Reproducible, in-process performance benchmarking suite for ascii-motion."""

from __future__ import annotations

import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from ascii_motion.config import RenderConfig
from ascii_motion.core.converter import FrameConverter
from ascii_motion.exporters.html import export_to_html
from ascii_motion.exporters.mp4 import export_to_mp4
from ascii_motion.utils.synthetic import create_synthetic_video, generate_synthetic_frame
from ascii_motion.video.probe import probe_video
from ascii_motion.video.reader import VideoStreamReader


def get_system_environment() -> dict[str, Any]:
    """Capture genuine hardware, OS, and software environment metadata."""
    return {
        "os": platform.platform(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "python_version": sys.version.split()[0],
        "numpy_version": np.__version__,
        "machine": platform.machine(),
    }


def run_microbenchmarks(warmup_runs: int = 5, test_runs: int = 15) -> list[dict[str, Any]]:
    """Benchmark the core frame conversion engine across resolutions and visual algorithms."""
    test_frame = generate_synthetic_frame(0, 100, width=640, height=360)
    results: list[dict[str, Any]] = []

    test_matrix = [
        # Resolutions (low, medium, high, ultra)
        {"name": "Low (60 cols, color)", "config": RenderConfig(width=60, style="color")},
        {"name": "Medium (100 cols, color)", "config": RenderConfig(width=100, style="color")},
        {"name": "High (160 cols, color)", "config": RenderConfig(width=160, style="color")},
        {"name": "Ultra (240 cols, color)", "config": RenderConfig(width=240, style="color")},
        # Styles (monochrome, green phosphor, amber phosphor)
        {
            "name": "Medium (100 cols, monochrome)",
            "config": RenderConfig(width=100, style="monochrome"),
        },
        {"name": "Medium (100 cols, green)", "config": RenderConfig(width=100, style="green")},
        {"name": "Medium (100 cols, amber)", "config": RenderConfig(width=100, style="amber")},
        # Advanced quality algorithms
        {
            "name": "Medium + Bayer Dithering",
            "config": RenderConfig(width=100, style="color", dithering="bayer"),
        },
        {
            "name": "Medium + Floyd-Steinberg Dithering",
            "config": RenderConfig(width=100, style="color", dithering="floyd_steinberg"),
        },
        {
            "name": "Medium + Sobel Edge Enhancement",
            "config": RenderConfig(width=100, style="color", edge_mode="sobel"),
        },
        {
            "name": "Medium + Temporal Smoothing",
            "config": RenderConfig(width=100, style="color", temporal_smoothing=0.4),
        },
    ]

    for item in test_matrix:
        name = item["name"]
        cfg: RenderConfig = item["config"]
        converter = FrameConverter(cfg)

        # Discarded warm-up runs
        for w in range(warmup_runs):
            converter.convert_frame(test_frame, w, 0.0)

        # Measured runs using high-resolution hardware performance counter
        timings: list[float] = []
        for r in range(test_runs):
            t0 = time.perf_counter()
            frame = converter.convert_frame(test_frame, r, 0.0)
            t1 = time.perf_counter()
            timings.append(t1 - t0)

        mean_s = statistics.mean(timings)
        median_s = statistics.median(timings)
        stdev_s = statistics.stdev(timings) if len(timings) > 1 else 0.0
        fps = 1.0 / mean_s if mean_s > 0 else 0.0

        results.append(
            {
                "test": name,
                "category": "microbenchmark",
                "grid_dimensions": [frame.width, frame.height],
                "total_cells": frame.width * frame.height,
                "mean_ms": round(mean_s * 1000.0, 3),
                "median_ms": round(median_s * 1000.0, 3),
                "stdev_ms": round(stdev_s * 1000.0, 3),
                "throughput_fps": round(fps, 1),
                "runs": test_runs,
                "warmup_runs": warmup_runs,
            }
        )

    return results


def run_end_to_end_benchmarks(
    sample_video_path: Path,
    warmup_runs: int = 2,
    test_runs: int = 3,
) -> list[dict[str, Any]]:
    """Benchmark complete end-to-end video conversion pipelines."""
    meta = probe_video(sample_video_path)
    tmp_dir = Path.cwd() / "tmp" / "benchmark_outputs"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    configs = [
        {
            "name": "E2E: MP4 Export (100 cols, color)",
            "fmt": "mp4",
            "config": RenderConfig(width=100, style="color"),
        },
        {
            "name": "E2E: HTML Export (100 cols, color)",
            "fmt": "html",
            "config": RenderConfig(width=100, style="color"),
        },
        {
            "name": "E2E: MP4 Export (60 cols, green phosphor)",
            "fmt": "mp4",
            "config": RenderConfig(width=60, style="green"),
        },
    ]

    results: list[dict[str, Any]] = []

    for item in configs:
        name = item["name"]
        fmt = item["fmt"]
        cfg: RenderConfig = item["config"]
        target_file = tmp_dir / f"bench_{fmt}_{int(time.time())}.{fmt}"

        def execute_pipeline(
            run_cfg: RenderConfig,
            run_fmt: str,
            run_out: Path,
        ) -> tuple[int, int]:
            conv = FrameConverter(run_cfg)
            frames = []
            with VideoStreamReader(sample_video_path, run_cfg, meta) as reader:
                for idx, ts, arr in reader.frames():
                    frames.append(conv.convert_frame(arr, idx, ts))

            if run_fmt == "mp4":
                export_to_mp4(frames, run_cfg, run_out, source_video=sample_video_path)
            elif run_fmt == "html":
                export_to_html(frames, run_cfg, run_out)

            size = run_out.stat().st_size if run_out.is_file() else 0
            if run_out.is_file():
                run_out.unlink()
            return len(frames), size

        # Warmup
        for _ in range(warmup_runs):
            execute_pipeline(cfg, fmt, target_file)

        timings: list[float] = []
        frame_counts: list[int] = []
        file_sizes: list[int] = []

        for _ in range(test_runs):
            t0 = time.perf_counter()
            f_count, f_size = execute_pipeline(cfg, fmt, target_file)
            t1 = time.perf_counter()
            timings.append(t1 - t0)
            frame_counts.append(f_count)
            file_sizes.append(f_size)

        mean_s = statistics.mean(timings)
        avg_frames = int(statistics.mean(frame_counts))
        throughput_fps = avg_frames / mean_s if mean_s > 0 else 0.0

        results.append(
            {
                "test": name,
                "category": "end_to_end",
                "format": fmt,
                "input_duration_s": meta.duration,
                "frames_processed": avg_frames,
                "mean_total_time_s": round(mean_s, 3),
                "throughput_fps": round(throughput_fps, 1),
                "output_size_bytes": int(statistics.mean(file_sizes)),
                "runs": test_runs,
            }
        )

    return results


def main() -> None:
    """Run benchmark suite and save genuine results."""
    print("=" * 60)
    print("ASCII-MOTION REPRODUCIBLE BENCHMARK SUITE")
    print("=" * 60)

    env = get_system_environment()
    print("Environment:", json.dumps(env, indent=2))

    # Ensure synthetic sample video
    sample_path = Path.cwd() / "assets" / "benchmark_sample.mp4"
    if not sample_path.is_file():
        print("Generating deterministic benchmark video (640x360, 2.0s, 30fps)...")
        create_synthetic_video(sample_path, duration=2.0, fps=30.0, width=640, height=360)

    print("\nRunning microbenchmarks (5 warmup runs, 15 measured runs)...")
    micro_results = run_microbenchmarks(warmup_runs=5, test_runs=15)
    for r in micro_results:
        print(
            f"  {r['test']:<42} -> {r['mean_ms']:>6.2f} ms ({r['throughput_fps']:>6.1f} FPS) [{r['grid_dimensions'][0]}x{r['grid_dimensions'][1]}]"
        )

    print("\nRunning end-to-end pipeline benchmarks (2 warmup, 3 measured runs)...")
    e2e_results = run_end_to_end_benchmarks(sample_path, warmup_runs=2, test_runs=3)
    for r in e2e_results:
        print(
            f"  {r['test']:<42} -> {r['mean_total_time_s']:>6.2f} s ({r['throughput_fps']:>6.1f} FPS, {r['output_size_bytes'] / 1024:.1f} KB)"
        )

    output_dir = Path.cwd() / "benchmarks"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_file = output_dir / "results.json"

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": env,
        "microbenchmarks": micro_results,
        "end_to_end": e2e_results,
    }

    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nSaved raw benchmark data to {report_file}")


if __name__ == "__main__":
    main()
