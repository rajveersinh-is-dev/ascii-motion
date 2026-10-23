# Architecture & Design Overview

`ascii-motion` is designed as a modular, high-throughput media rendering engine. It provides both a scriptable Command-Line Interface (CLI) and an interactive local Web Studio sharing an identical core conversion engine.

```
                          ┌─────────────────────────────┐
                          │     Input Video Source      │
                          │   (MP4, MOV, WebM, AVI)     │
                          └──────────────┬──────────────┘
                                         │
                                         ▼
                          ┌─────────────────────────────┐
                          │   VideoStreamReader (C/FFmpeg)
                          │   - Probing & Audio Detect  │
                          │   - Stream-level Downscale  │
                          │   - Rawvideo RGB24 Pipe     │
                          └──────────────┬──────────────┘
                                         │
                                         ▼
                          ┌─────────────────────────────┐
                          │  FrameConverter Core Engine │
                          │   - Rec. 709 Luminance      │
                          │   - Tone Mapping & Gamma    │
                          │   - Temporal Smoothing      │
                          │   - Bayer / Floyd-Steinberg │
                          │   - Vectorized Char Lookup  │
                          │   - Palette & Color Map     │
                          └──────────────┬──────────────┘
                                         │
                  ┌──────────────────────┼──────────────────────┐
                  │                      │                      │
                  ▼                      ▼                      ▼
        ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
        │ Terminal Output  │   │  HTML5 Animation │   │ Video Exporter   │
        │ - 24-bit ANSI    │   │ - Standalone JS  │   │ - H.264 MP4      │
        │ - Cursor pacing  │   │ - HTML5 Canvas   │   │ - Animated GIF   │
        │ - Signal clean   │   │ - 100% Offline   │   │ - Audio Passthru │
        └──────────────────┘   └──────────────────┘   └──────────────────┘
```

---

## 1. Directory Structure

```
ascii-motion/
├── src/ascii_motion/
│   ├── config.py           # Pydantic models for RenderConfig & presets
│   ├── cli.py              # CLI entrypoint with argparse & reporting
│   ├── core/
│   │   ├── converter.py    # AsciiFrame dataclass & FrameConverter pipeline
│   │   ├── perceptual.py   # BT.709/BT.601 luminance & tone adjustments
│   │   ├── ramps.py        # Predefined character ramps & density estimator
│   │   ├── dithering.py    # Recursive Bayer & Floyd-Steinberg dithering
│   │   ├── edge.py         # Vectorized Sobel convolution & stroke mapper
│   │   └── color.py        # ANSI truecolor formatting & retro palettes
│   ├── video/
│   │   ├── ffmpeg.py       # Binary discovery (system + imageio-ffmpeg)
│   │   ├── probe.py        # Stream inspection & metadata parsing
│   │   └── reader.py       # Streaming frame decoder with bounded queues
│   ├── exporters/
│   │   ├── terminal.py     # Real-time ANSI terminal player
│   │   ├── html.py         # Self-contained HTML5 canvas animation exporter
│   │   ├── mp4.py          # ASCII rasterizer & FFmpeg H.264 video writer
│   │   ├── gif.py          # Optimized animated GIF exporter
│   │   └── text.py         # Plain text and ANSI sequence file generator
│   └── api/
│       ├── app.py          # FastAPI application & static SPA mount
│       ├── routes.py       # REST endpoints for preview, upload, sample, jobs
│       └── jobs.py         # Thread-safe background JobManager & cancellation
├── web/                    # React 18 + TypeScript + Vite frontend studio
│   ├── src/
│   │   ├── App.tsx         # Studio root orchestrator
│   │   ├── components/     # Upload, Preview, Settings, Export panels
│   │   └── index.css       # Creative-tool dark design system
├── tests/                  # 52 automated pytest test cases
├── benchmarks/             # In-process reproducible benchmark suite
├── scripts/                # Synthetic video & demo generation utilities
└── assets/                 # Verified README demonstration assets
```

---

## 2. Resource & Memory Guarantees

1. **Streaming Frame Pipeline**: Frames are decoded sequentially from FFmpeg standard output into small fixed buffers (`H * W * 3` bytes). The process memory footprint remains constant (~40-60 MB) even when processing hour-long videos.
2. **Pipe Deadlock Prevention**: Subprocess standard error buffers are directed to disk-backed temporary files (`tempfile.TemporaryFile()`) or `DEVNULL` during streaming, avoiding the 4KB OS pipe buffer deadlock on Windows and UNIX platforms.
3. **Subprocess Life-Cycle & Cancellation**: Background tasks and readers implement context manager protocols (`__enter__` / `__exit__`) and explicit termination routines (`terminate()`, `kill()`, `wait()`), ensuring no zombie processes are left on cancellation or interrupt.
