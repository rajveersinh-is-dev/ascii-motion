import React, { useEffect, useRef, useState } from "react";
import { PreviewData, VideoMetadata } from "../types";

interface PreviewSectionProps {
  preview: PreviewData | null;
  metadata: VideoMetadata | null;
  timestamp: number;
  onSeek: (newTime: number) => void;
  loading: boolean;
}

export const PreviewSection: React.FC<PreviewSectionProps> = ({
  preview,
  metadata,
  timestamp,
  onSeek,
  loading,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [copied, setCopied] = useState(false);

  // Canvas character rendering
  useEffect(() => {
    if (!preview || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const charW = 8;
    const charH = 14;
    canvas.width = preview.width * charW;
    canvas.height = preview.height * charH;

    // Fill background
    ctx.fillStyle = preview.background_color || "#000000";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.font = '12px "JetBrains Mono", Consolas, monospace';
    ctx.textBaseline = "top";

    const hasColors = Boolean(preview.colors && preview.colors.length > 0);

    for (let y = 0; y < preview.height; y++) {
      const line = preview.lines[y] || "";
      const yPos = y * charH;

      if (!hasColors) {
        ctx.fillStyle = preview.foreground_color || "#FFFFFF";
        ctx.fillText(line, 0, yPos);
      } else {
        const rowColors = preview.colors![y];
        for (let x = 0; x < preview.width; x++) {
          const ch = line[x] || " ";
          ctx.fillStyle = rowColors?.[x] || preview.foreground_color || "#FFFFFF";
          ctx.fillText(ch, x * charW, yPos);
        }
      }
    }
  }, [preview]);

  // Playback timer
  useEffect(() => {
    if (!isPlaying || !metadata) return;
    const interval = setInterval(() => {
      const next = timestamp + 0.1;
      if (next >= metadata.duration) {
        onSeek(0.0);
      } else {
        onSeek(next);
      }
    }, 100);
    return () => clearInterval(interval);
  }, [isPlaying, metadata, timestamp, onSeek]);

  const copyToClipboard = () => {
    if (!preview) return;
    const text = preview.lines.join("\n");
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  const maxDuration = metadata ? metadata.duration : 10.0;

  return (
    <div className="panel" style={{ flex: 1 }}>
      <div className="panel-header">
        <span className="panel-title">Interactive ASCII Viewport</span>
        {preview && (
          <span className="meta-badge">
            Grid: <span>{preview.width} x {preview.height}</span> cells
          </span>
        )}
      </div>

      <div className="preview-viewport">
        {loading && (
          <div style={{ position: "absolute", top: 12, right: 12, background: "rgba(0,0,0,0.6)", padding: "4px 8px", borderRadius: 4, fontSize: 11, color: "var(--accent-primary)" }}>
            Rendering...
          </div>
        )}
        {preview ? (
          <canvas ref={canvasRef} className="ascii-canvas" />
        ) : (
          <div style={{ color: "var(--text-muted)", fontSize: 14 }}>
            Upload a video or click "Use Sample Demo Video" to begin.
          </div>
        )}
      </div>

      <div className="playback-controls">
        <div className="timeline-row">
          <input
            type="range"
            className="scrubber"
            min={0}
            max={maxDuration}
            step={0.05}
            value={timestamp}
            onChange={(e) => onSeek(parseFloat(e.target.value))}
          />
          <span className="timecode">
            {timestamp.toFixed(2)}s / {maxDuration.toFixed(2)}s
          </span>
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", gap: "8px" }}>
            <button
              className={`btn btn-sm ${isPlaying ? "active" : ""}`}
              onClick={() => setIsPlaying(!isPlaying)}
            >
              {isPlaying ? "Pause" : "Play"}
            </button>
            <button
              className="btn btn-sm"
              onClick={() => onSeek(Math.max(0, timestamp - 0.1))}
            >
              -0.1s
            </button>
            <button
              className="btn btn-sm"
              onClick={() => onSeek(Math.min(maxDuration, timestamp + 0.1))}
            >
              +0.1s
            </button>
          </div>

          <button
            className="btn btn-sm"
            onClick={copyToClipboard}
            disabled={!preview}
          >
            {copied ? "Copied!" : "Copy ASCII Text"}
          </button>
        </div>
      </div>
    </div>
  );
};
