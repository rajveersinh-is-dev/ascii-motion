import React from "react";
import { ColorStyle, DitherMode, EdgeMode, RenderConfig, ResolutionPreset } from "../types";

interface SettingsPanelProps {
  config: RenderConfig;
  onChange: (updater: (prev: RenderConfig) => RenderConfig) => void;
  onReset: () => void;
  ramps: Record<string, string>;
}

export const SettingsPanel: React.FC<SettingsPanelProps> = ({
  config,
  onChange,
  onReset,
  ramps,
}) => {
  const setPreset = (preset: ResolutionPreset) => {
    const widths: Record<string, number> = {
      low: 60,
      medium: 100,
      high: 160,
      ultra: 240,
    };
    onChange((prev) => ({
      ...prev,
      preset,
      width: widths[preset] || prev.width,
    }));
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Rendering Engine Settings</span>
        <button className="btn btn-sm" onClick={onReset}>
          Reset
        </button>
      </div>

      {/* Resolution & Presets */}
      <div className="control-group">
        <div className="control-label">
          <span>Resolution Preset</span>
          <span className="control-val">{config.width} cols</span>
        </div>
        <div className="pill-group">
          {(["low", "medium", "high", "ultra", "custom"] as ResolutionPreset[]).map((p) => (
            <button
              key={p}
              className={`pill-btn ${config.preset === p ? "active" : ""}`}
              onClick={() => setPreset(p)}
            >
              {p.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {config.preset === "custom" && (
        <div className="control-group">
          <div className="control-label">
            <span>Custom Width (Columns)</span>
            <span className="control-val">{config.width}</span>
          </div>
          <input
            type="range"
            className="control-slider"
            min={20}
            max={320}
            value={config.width}
            onChange={(e) => {
              const val = parseInt(e.target.value, 10);
              onChange((prev) => ({ ...prev, width: val }));
            }}
          />
        </div>
      )}

      {/* Visual Style */}
      <div className="control-group">
        <div className="control-label">
          <span>Visual Style</span>
          <span className="control-val">{config.style}</span>
        </div>
        <div className="pill-group">
          {(["color", "monochrome", "green", "amber"] as ColorStyle[]).map((s) => (
            <button
              key={s}
              className={`pill-btn ${config.style === s ? "active" : ""}`}
              onClick={() => onChange((prev) => ({ ...prev, style: s }))}
            >
              {s.slice(0, 5).toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Character Ramp */}
      <div className="control-group">
        <div className="control-label">
          <span>Character Ramp</span>
        </div>
        <select
          value={config.ramp_name}
          onChange={(e) => onChange((prev) => ({ ...prev, ramp_name: e.target.value }))}
        >
          {Object.keys(ramps).map((name) => (
            <option key={name} value={name}>
              {name} ({ramps[name].length} chars)
            </option>
          ))}
          <option value="custom">Custom Ramp</option>
        </select>
        {config.ramp_name === "custom" && (
          <input
            type="text"
            placeholder="e.g.  .:-=+*#%@"
            value={config.custom_ramp || ""}
            onChange={(e) => onChange((prev) => ({ ...prev, custom_ramp: e.target.value }))}
            style={{ marginTop: 6 }}
          />
        )}
      </div>

      {/* Tone Adjustments */}
      <div className="control-group">
        <div className="control-label">
          <span>Brightness</span>
          <span className="control-val">{config.brightness.toFixed(2)}x</span>
        </div>
        <input
          type="range"
          className="control-slider"
          min={0.2}
          max={2.5}
          step={0.05}
          value={config.brightness}
          onChange={(e) => {
            const val = parseFloat(e.target.value);
            onChange((prev) => ({ ...prev, brightness: val }));
          }}
        />
      </div>

      <div className="control-group">
        <div className="control-label">
          <span>Contrast</span>
          <span className="control-val">{config.contrast.toFixed(2)}x</span>
        </div>
        <input
          type="range"
          className="control-slider"
          min={0.2}
          max={2.5}
          step={0.05}
          value={config.contrast}
          onChange={(e) => {
            const val = parseFloat(e.target.value);
            onChange((prev) => ({ ...prev, contrast: val }));
          }}
        />
      </div>

      <div className="control-group">
        <div className="control-label">
          <span>Gamma</span>
          <span className="control-val">{config.gamma.toFixed(2)}</span>
        </div>
        <input
          type="range"
          className="control-slider"
          min={0.2}
          max={2.5}
          step={0.05}
          value={config.gamma}
          onChange={(e) => {
            const val = parseFloat(e.target.value);
            onChange((prev) => ({ ...prev, gamma: val }));
          }}
        />
      </div>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>Invert Luminance</span>
        <button
          className={`btn btn-sm ${config.invert ? "active" : ""}`}
          onClick={() => onChange((prev) => ({ ...prev, invert: !prev.invert }))}
        >
          {config.invert ? "Inverted" : "Normal"}
        </button>
      </div>

      {/* Advanced Quality */}
      <div className="control-group" style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: 12 }}>
        <div className="control-label">
          <span>Dithering</span>
          <span className="control-val">{config.dithering}</span>
        </div>
        <div className="pill-group">
          {(["none", "bayer", "floyd_steinberg"] as DitherMode[]).map((d) => (
            <button
              key={d}
              className={`pill-btn ${config.dithering === d ? "active" : ""}`}
              onClick={() => onChange((prev) => ({ ...prev, dithering: d }))}
            >
              {d === "floyd_steinberg" ? "F-S" : d.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <div className="control-group">
        <div className="control-label">
          <span>Edge Enhancement</span>
          <span className="control-val">{config.edge_mode}</span>
        </div>
        <div className="pill-group">
          {(["none", "sobel"] as EdgeMode[]).map((e) => (
            <button
              key={e}
              className={`pill-btn ${config.edge_mode === e ? "active" : ""}`}
              onClick={() => onChange((prev) => ({ ...prev, edge_mode: e }))}
            >
              {e.toUpperCase()}
            </button>
          ))}
        </div>
        {config.edge_mode === "sobel" && (
          <div style={{ marginTop: 6 }}>
            <div className="control-label">
              <span>Edge Strength</span>
              <span className="control-val">{config.edge_strength.toFixed(2)}</span>
            </div>
            <input
              type="range"
              className="control-slider"
              min={0.1}
              max={1.5}
              step={0.05}
              value={config.edge_strength}
              onChange={(e) => {
                const val = parseFloat(e.target.value);
                onChange((prev) => ({ ...prev, edge_strength: val }));
              }}
            />
          </div>
        )}
      </div>

      <div className="control-group">
        <div className="control-label">
          <span>Temporal Smoothing</span>
          <span className="control-val">{config.temporal_smoothing.toFixed(2)}</span>
        </div>
        <input
          type="range"
          className="control-slider"
          min={0.0}
          max={0.8}
          step={0.05}
          value={config.temporal_smoothing}
          onChange={(e) => {
            const val = parseFloat(e.target.value);
            onChange((prev) => ({ ...prev, temporal_smoothing: val }));
          }}
        />
      </div>
    </div>
  );
};
