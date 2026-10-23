"""Standalone HTML animation exporter with interactive playback controls."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ascii_motion.config import RenderConfig
from ascii_motion.core.converter import AsciiFrame


def export_to_html(
    frames: list[AsciiFrame],
    config: RenderConfig,
    output_path: str | Path,
    title: str = "ascii-motion Player",
) -> Path:
    """Export a list of AsciiFrame instances to a self-contained offline HTML animation file.

    Args:
        frames: Rendered ASCII frames.
        config: Render configuration used.
        output_path: Target .html file path.
        title: Title of the HTML page.

    Returns:
        Path to the written HTML file.
    """
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    if not frames:
        raise ValueError("Cannot export HTML with zero frames.")

    width = frames[0].width
    height = frames[0].height
    fps = config.target_fps or 24.0

    # Package frames into compact JSON
    packed_frames: list[dict[str, Any]] = []
    is_color = config.style == "color"

    for f in frames:
        # Convert 2D char array to list of strings
        row_strings = ["".join(row) for row in f.chars]
        frame_dict: dict[str, Any] = {"lines": row_strings}

        if is_color:
            # Flatten colors to compact hex or run-length hex
            # To balance size and performance, encode each row as array of hex colors
            row_colors: list[list[str]] = []
            for y in range(f.height):
                r_colors = [
                    f"#{f.colors[y, x, 0]:02x}{f.colors[y, x, 1]:02x}{f.colors[y, x, 2]:02x}"
                    for x in range(f.width)
                ]
                row_colors.append(r_colors)
            frame_dict["colors"] = row_colors

        packed_frames.append(frame_dict)

    data_payload = {
        "title": title,
        "width": width,
        "height": height,
        "fps": fps,
        "style": config.style,
        "fg": config.foreground_color,
        "bg": config.background_color,
        "frameCount": len(frames),
        "frames": packed_frames,
    }

    # Safe JSON serialization (escaping <, >, & to prevent XSS / script breakage)
    json_str = (
        json.dumps(data_payload)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )

    # Monospace font styling based on style
    css_fg = config.foreground_color
    if config.style == "green":
        css_fg = "#33FF33"
    elif config.style == "amber":
        css_fg = "#FFB000"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  :root {{
    --bg-color: {config.background_color};
    --fg-color: {css_fg};
    --surface-color: #12141c;
    --surface-border: #232838;
    --accent-color: #3b82f6;
    --accent-hover: #2563eb;
    --text-muted: #8b949e;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background-color: var(--bg-color);
    color: #e6edf3;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: 16px;
    overflow-x: hidden;
  }}
  .player-wrapper {{
    background: var(--surface-color);
    border: 1px solid var(--surface-border);
    border-radius: 12px;
    box-shadow: 0 16px 32px rgba(0, 0, 0, 0.4);
    max-width: 98vw;
    width: fit-content;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }}
  .player-header {{
    padding: 12px 18px;
    border-bottom: 1px solid var(--surface-border);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .player-title {{
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.5px;
    color: #f0f6fc;
  }}
  .player-badge {{
    font-size: 11px;
    background: #1f2430;
    color: var(--accent-color);
    padding: 2px 8px;
    border-radius: 6px;
    font-family: monospace;
  }}
  .canvas-container {{
    background: {config.background_color};
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 12px;
    overflow: auto;
    max-height: 80vh;
  }}
  canvas {{
    display: block;
    image-rendering: pixelated;
    border-radius: 4px;
  }}
  .controls-panel {{
    background: #0d1017;
    border-top: 1px solid var(--surface-border);
    padding: 12px 18px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }}
  .timeline-bar {{
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  .timeline-slider {{
    flex: 1;
    -webkit-appearance: none;
    appearance: none;
    height: 6px;
    border-radius: 3px;
    background: #21262d;
    outline: none;
    cursor: pointer;
  }}
  .timeline-slider::-webkit-slider-thumb {{
    -webkit-appearance: none;
    appearance: none;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: var(--accent-color);
    cursor: pointer;
  }}
  .time-display {{
    font-family: monospace;
    font-size: 12px;
    color: var(--text-muted);
    min-width: 90px;
    text-align: right;
  }}
  .buttons-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
  }}
  .button-group {{
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  button {{
    background: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s ease;
  }}
  button:hover {{
    background: #30363d;
    color: #f0f6fc;
    border-color: #8b949e;
  }}
  button.active {{
    background: var(--accent-color);
    color: #ffffff;
    border-color: var(--accent-hover);
  }}
  select {{
    background: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 5px 8px;
    font-size: 12px;
    outline: none;
    cursor: pointer;
  }}
</style>
</head>
<body>

<div class="player-wrapper">
  <div class="player-header">
    <span class="player-title">{title}</span>
    <span class="player-badge">{width}x{height} | {fps:.1f} FPS | {config.style.upper()}</span>
  </div>

  <div class="canvas-container">
    <canvas id="asciiCanvas"></canvas>
  </div>

  <div class="controls-panel">
    <div class="timeline-bar">
      <input type="range" id="seekSlider" class="timeline-slider" min="0" max="{len(frames) - 1}" value="0">
      <span id="timeDisplay" class="time-display">0:00 / 0:00</span>
    </div>

    <div class="buttons-row">
      <div class="button-group">
        <button id="btnPlay">Pause</button>
        <button id="btnPrev">Step -</button>
        <button id="btnNext">Step +</button>
        <button id="btnLoop" class="active">Loop</button>
      </div>

      <div class="button-group">
        <label for="speedSelect" style="font-size: 12px; color: var(--text-muted);">Speed:</label>
        <select id="speedSelect">
          <option value="0.5">0.5x</option>
          <option value="1.0" selected>1.0x</option>
          <option value="1.5">1.5x</option>
          <option value="2.0">2.0x</option>
        </select>
        <button id="btnCopy">Copy Frame</button>
      </div>
    </div>
  </div>
</div>

<script>
(function() {{
  const DATA = {json_str};
  const canvas = document.getElementById('asciiCanvas');
  const ctx = canvas.getContext('2d');
  const btnPlay = document.getElementById('btnPlay');
  const btnPrev = document.getElementById('btnPrev');
  const btnNext = document.getElementById('btnNext');
  const btnLoop = document.getElementById('btnLoop');
  const btnCopy = document.getElementById('btnCopy');
  const speedSelect = document.getElementById('speedSelect');
  const seekSlider = document.getElementById('seekSlider');
  const timeDisplay = document.getElementById('timeDisplay');

  let currentFrameIdx = 0;
  let isPlaying = true;
  let loop = true;
  let playbackSpeed = 1.0;
  let lastFrameTime = performance.now();
  let animationId = null;

  // Glyph geometry for crisp canvas rendering
  const charWidth = 8;
  const charHeight = 14;
  canvas.width = DATA.width * charWidth;
  canvas.height = DATA.height * charHeight;

  ctx.font = '12px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace';
  ctx.textBaseline = 'top';

  function formatTime(sec) {{
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    const ms = Math.floor((sec % 1) * 10);
    return `${{m}}:${{s < 10 ? '0' : ''}}${{s}}.${{ms}}`;
  }}

  function renderFrame(idx) {{
    const frame = DATA.frames[idx];
    if (!frame) return;

    ctx.fillStyle = DATA.bg;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const hasColors = Boolean(frame.colors);

    for (let y = 0; y < DATA.height; y++) {{
      const line = frame.lines[y];
      const yPos = y * charHeight;

      if (!hasColors) {{
        ctx.fillStyle = DATA.style === 'green' ? '#33FF33' : (DATA.style === 'amber' ? '#FFB000' : DATA.fg);
        ctx.fillText(line, 0, yPos);
      }} else {{
        const rowColors = frame.colors[y];
        for (let x = 0; x < DATA.width; x++) {{
          const ch = line[x] || ' ';
          ctx.fillStyle = rowColors[x] || DATA.fg;
          ctx.fillText(ch, x * charWidth, yPos);
        }}
      }}
    }}

    seekSlider.value = idx;
    const currentSec = idx / DATA.fps;
    const totalSec = DATA.frameCount / DATA.fps;
    timeDisplay.textContent = `${{formatTime(currentSec)}} / ${{formatTime(totalSec)}}`;
  }}

  function loopAnimation(now) {{
    if (isPlaying) {{
      const interval = (1000 / DATA.fps) / playbackSpeed;
      const elapsed = now - lastFrameTime;
      if (elapsed >= interval) {{
        currentFrameIdx++;
        if (currentFrameIdx >= DATA.frameCount) {{
          if (loop) {{
            currentFrameIdx = 0;
          }} else {{
            currentFrameIdx = DATA.frameCount - 1;
            isPlaying = false;
            btnPlay.textContent = 'Play';
          }}
        }}
        renderFrame(currentFrameIdx);
        lastFrameTime = now - (elapsed % interval);
      }}
    }}
    animationId = requestAnimationFrame(loopAnimation);
  }}

  btnPlay.addEventListener('click', () => {{
    isPlaying = !isPlaying;
    btnPlay.textContent = isPlaying ? 'Pause' : 'Play';
    if (isPlaying) lastFrameTime = performance.now();
  }});

  btnPrev.addEventListener('click', () => {{
    isPlaying = false;
    btnPlay.textContent = 'Play';
    currentFrameIdx = Math.max(0, currentFrameIdx - 1);
    renderFrame(currentFrameIdx);
  }});

  btnNext.addEventListener('click', () => {{
    isPlaying = false;
    btnPlay.textContent = 'Play';
    currentFrameIdx = Math.min(DATA.frameCount - 1, currentFrameIdx + 1);
    renderFrame(currentFrameIdx);
  }});

  btnLoop.addEventListener('click', () => {{
    loop = !loop;
    btnLoop.classList.toggle('active', loop);
  }});

  speedSelect.addEventListener('change', (e) => {{
    playbackSpeed = parseFloat(e.target.value);
  }});

  seekSlider.addEventListener('input', (e) => {{
    currentFrameIdx = parseInt(e.target.value, 10);
    renderFrame(currentFrameIdx);
  }});

  btnCopy.addEventListener('click', () => {{
    const frame = DATA.frames[currentFrameIdx];
    if (frame) {{
      const text = frame.lines.join('\\n');
      navigator.clipboard.writeText(text).then(() => {{
        const orig = btnCopy.textContent;
        btnCopy.textContent = 'Copied!';
        setTimeout(() => {{ btnCopy.textContent = orig; }}, 1500);
      }});
    }}
  }});

  // Initial draw
  renderFrame(0);
  animationId = requestAnimationFrame(loopAnimation);
}})();
</script>
</body>
</html>"""

    out_file.write_text(html_content, encoding="utf-8")
    return out_file
