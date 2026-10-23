# Contributing to ascii-motion

Thank you for your interest in contributing to `ascii-motion`! We welcome contributions to the core rendering engine, video streaming pipeline, exporters, CLI, and web studio.

---

## Development Setup

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- FFmpeg (either on system PATH or via `imageio-ffmpeg`)

### 1. Python Environment Setup
```bash
# Clone the repository
git clone https://github.com/rajveersinh-is-dev/ascii-motion.git
cd ascii-motion

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install dependencies in editable mode
pip install -e ".[dev]"
```

### 2. Frontend Studio Setup
```bash
cd web
npm install
npm run build
cd ..
```

---

## Code Quality Standards

Before submitting a Pull Request, verify that all checks pass:

```bash
# Run pytest test suite (52 tests)
pytest -v

# Run ruff linter
ruff check .

# Run ruff formatter
ruff format --check .

# Build frontend
cd web && npm run build && cd ..
```

### Pull Request Guidelines
1. Ensure all new features are accompanied by automated unit or integration tests in `tests/`.
2. Do not introduce pre-loaded lookup tables or synthetic benchmark numbers.
3. Keep subprocess invocations safe: pass argument arrays (never shell=True with unescaped user input) and handle standard error safely without unbounded pipe buffers.
