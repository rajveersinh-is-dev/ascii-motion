import React, { useState } from "react";
import { JobStatus, RenderConfig } from "../types";

interface ExportSectionProps {
  videoPath: string | null;
  filename: string | null;
  config: RenderConfig;
  onStartExport: (format: string) => void;
  onCancelJob: (jobId: string) => void;
  activeJob: JobStatus | null;
}

export const ExportSection: React.FC<ExportSectionProps> = ({
  videoPath,
  filename,
  config,
  onStartExport,
  onCancelJob,
  activeJob,
}) => {
  const [selectedFormat, setSelectedFormat] = useState<string>("mp4");
  const [copiedCli, setCopiedCli] = useState(false);

  // Build reproducible CLI command based on current config
  const targetExt = selectedFormat === "ansi" ? "ans" : selectedFormat;
  const outName = filename ? `${filename.replace(/\.[^.]+$/, "")}.${targetExt}` : `output.${targetExt}`;
  const inputArg = filename || "input.mp4";

  let cliCmd = `ascii-motion ${inputArg} --output ${outName} --preset ${config.preset} --style ${config.style}`;
  if (config.preset === "custom") {
    cliCmd += ` --width ${config.width}`;
  }
  if (config.ramp_name !== "standard_10") {
    cliCmd += ` --ramp ${config.ramp_name}`;
  }
  if (config.brightness !== 1.0) {
    cliCmd += ` --brightness ${config.brightness.toFixed(2)}`;
  }
  if (config.contrast !== 1.0) {
    cliCmd += ` --contrast ${config.contrast.toFixed(2)}`;
  }
  if (config.invert) {
    cliCmd += ` --invert`;
  }
  if (config.dithering !== "none") {
    cliCmd += ` --dither ${config.dithering}`;
  }
  if (config.edge_mode !== "none") {
    cliCmd += ` --edge ${config.edge_mode}`;
  }

  const copyCli = () => {
    navigator.clipboard.writeText(cliCmd).then(() => {
      setCopiedCli(true);
      setTimeout(() => setCopiedCli(false), 1500);
    });
  };

  const isExporting = activeJob && (activeJob.status === "pending" || activeJob.status === "processing");

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Export & Automation</span>
      </div>

      <div className="control-group">
        <div className="control-label">
          <span>Target Export Format</span>
        </div>
        <div className="pill-group">
          {[
            { id: "mp4", label: "MP4 Video" },
            { id: "html", label: "HTML5 Player" },
            { id: "gif", label: "Animated GIF" },
            { id: "txt", label: "Plain Text" },
          ].map((fmt) => (
            <button
              key={fmt.id}
              className={`pill-btn ${selectedFormat === fmt.id ? "active" : ""}`}
              onClick={() => setSelectedFormat(fmt.id)}
            >
              {fmt.label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: "flex", gap: "10px" }}>
        <button
          className="btn btn-primary"
          style={{ flex: 1, padding: "10px" }}
          onClick={() => onStartExport(selectedFormat)}
          disabled={!videoPath || Boolean(isExporting)}
        >
          {isExporting ? "Rendering Export..." : `Render & Export ${selectedFormat.toUpperCase()}`}
        </button>
      </div>

      {activeJob && (
        <div className="progress-container">
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
            <span style={{ color: "var(--text-secondary)" }}>
              Status: <strong>{activeJob.status.toUpperCase()}</strong>
              {activeJob.total_frames > 0 && ` (${activeJob.processed_frames} / ${activeJob.total_frames} frames)`}
            </span>
            <span style={{ color: "var(--accent-primary)", fontFamily: "var(--font-mono)" }}>
              {activeJob.progress.toFixed(0)}%
            </span>
          </div>

          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${activeJob.progress}%` }} />
          </div>

          {isExporting && (
            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 4 }}>
              <button
                className="btn btn-sm"
                style={{ color: "#ef4444" }}
                onClick={() => onCancelJob(activeJob.job_id)}
              >
                Cancel Job
              </button>
            </div>
          )}

          {activeJob.status === "completed" && activeJob.output_available && (
            <a
              href={`/api/jobs/${activeJob.job_id}/download`}
              download
              className="btn btn-secondary"
              style={{ textDecoration: "none", marginTop: 8 }}
            >
              Download Exported {selectedFormat.toUpperCase()}
            </a>
          )}

          {activeJob.status === "failed" && (
            <div style={{ color: "#ef4444", fontSize: 12, marginTop: 4 }}>
              Error: {activeJob.error}
            </div>
          )}
        </div>
      )}

      {/* Reproducible CLI Command Box */}
      <div className="control-group" style={{ marginTop: 10 }}>
        <div className="control-label">
          <span>Reproducible CLI Command</span>
        </div>
        <div className="code-box">
          <code>{cliCmd}</code>
          <button className="btn btn-sm copy-btn" onClick={copyCli}>
            {copiedCli ? "Copied" : "Copy"}
          </button>
        </div>
      </div>
    </div>
  );
};
