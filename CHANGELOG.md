# Changelog

All notable changes to `ascii-motion` are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-10-23

### Added
- **Core Vectorized Rendering Core**:
  - High-performance perceptual luminance mapping using ITU-R BT.709 and BT.601 standards.
  - Aspect ratio correction preserving true geometric proportions for rectangular monospace character cells.
  - Tone adjustments: brightness, contrast centering, gamma power law, and inversion.
  - Dynamic Bayer ordered dithering generated from recursive tensor products.
  - Floyd-Steinberg error diffusion dithering.
  - Vectorized Sobel convolution edge enhancement and directional stroke replacement (`-`, `|`, `/`, `\`).
  - Adaptive temporal smoothing with motion-decay dampening.
  - Empirical glyph density measurement from first principles using raster fill analysis.
- **Video Subsystem**:
  - FFmpeg metadata probe supporting duration, frame rates, video/audio codecs, and rotation matrices.
  - Memory-bounded streaming frame reader piping raw RGB24 frames with SIMD downscaling.
  - Robust FFmpeg discovery supporting system binaries, custom environment variables, and `imageio-ffmpeg`.
- **Exporters**:
  - Interactive ANSI terminal playback with flicker-free cursor pacing and graceful interrupt restoration.
  - Standalone single-file HTML5 animation player with playback scrubber, speed controls, loop toggle, and zero CDN dependencies.
  - MP4 video renderer utilizing Pillow monospace font rasterization and H.264 pipe encoding with audio passthrough.
  - Animated GIF exporter with adaptive 256-color palette quantization.
  - Plain text and ANSI escape sequence file exports (`.txt`, `.ans`).
- **Command-Line Interface (CLI)**:
  - Complete argument parser supporting resolution presets, custom dimensions, color styles, dithering, and trimming.
  - Real-time progress updates and machine-readable JSON execution reports (`--report`).
  - Configuration loader and serializer (`--config`, `--save-config`).
- **Interactive Web Studio**:
  - React 18 + TypeScript + Vite modern creative-tool studio with dark glassmorphism design system.
  - Drag-and-drop video upload and built-in synthetic sample generator.
  - Live interactive HTML5 canvas ASCII viewport with real-time parameter tuning.
  - Asynchronous background job manager with cancellation and progress polling.
- **Verification & Testing**:
  - 52 passing automated tests across unit, integration, and mathematical invariant categories.
  - Reproducible benchmark suite with warmups and statistical metrics.
