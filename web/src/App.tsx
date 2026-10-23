import React, { useCallback, useEffect, useRef, useState } from "react";
import { Header } from "./components/Header";
import { UploadSection } from "./components/UploadSection";
import { PreviewSection } from "./components/PreviewSection";
import { SettingsPanel } from "./components/SettingsPanel";
import { ExportSection } from "./components/ExportSection";
import { JobStatus, PreviewData, RenderConfig, VideoMetadata } from "./types";

const DEFAULT_CONFIG: RenderConfig = {
  preset: "medium",
  width: 100,
  height: null,
  char_aspect_ratio: 0.5,
  target_fps: null,
  trim_start: 0.0,
  trim_end: null,
  max_duration: null,
  max_frames: null,
  brightness: 1.0,
  contrast: 1.0,
  gamma: 1.0,
  invert: false,
  ramp_name: "standard_10",
  custom_ramp: null,
  style: "color",
  foreground_color: "#FFFFFF",
  background_color: "#000000",
  dithering: "none",
  edge_mode: "none",
  edge_strength: 0.5,
  temporal_smoothing: 0.0,
};

export const App: React.FC = () => {
  const [videoPath, setVideoPath] = useState<string | null>(null);
  const [filename, setFilename] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<VideoMetadata | null>(null);
  const [config, setConfig] = useState<RenderConfig>(DEFAULT_CONFIG);
  const [timestamp, setTimestamp] = useState<number>(0.0);
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [ramps, setRamps] = useState<Record<string, string>>({});
  const [activeJob, setActiveJob] = useState<JobStatus | null>(null);
  const [loadingSample, setLoadingSample] = useState<boolean>(false);
  const [loadingPreview, setLoadingPreview] = useState<boolean>(false);

  const previewTimeoutRef = useRef<number | null>(null);

  // Load ramps list
  useEffect(() => {
    fetch("/api/ramps")
      .then((res) => res.json())
      .then((data) => setRamps(data))
      .catch((err) => console.error("Error loading ramps:", err));
  }, []);

  // Fetch preview frame (debounced)
  const fetchPreview = useCallback(
    (vPath: string, time: number, cfg: RenderConfig) => {
      if (previewTimeoutRef.current) {
        clearTimeout(previewTimeoutRef.current);
      }
      previewTimeoutRef.current = window.setTimeout(async () => {
        setLoadingPreview(true);
        try {
          const res = await fetch("/api/preview", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              video_path: vPath,
              timestamp: time,
              config: cfg,
            }),
          });
          if (res.ok) {
            const data: PreviewData = await res.json();
            setPreview(data);
          }
        } catch (err) {
          console.error("Preview fetch error:", err);
        } finally {
          setLoadingPreview(false);
        }
      }, 80);
    },
    []
  );

  // Trigger preview when videoPath, timestamp, or config changes
  useEffect(() => {
    if (videoPath) {
      fetchPreview(videoPath, timestamp, config);
    }
  }, [videoPath, timestamp, config, fetchPreview]);

  // Load sample video
  const handleLoadSample = async () => {
    setLoadingSample(true);
    try {
      const res = await fetch("/api/sample");
      if (!res.ok) throw new Error("Failed to load sample video");
      const data = await res.json();
      setVideoPath(data.path);
      setFilename(data.filename);
      setMetadata(data.metadata);
      setTimestamp(0.0);
    } catch (err: any) {
      alert(`Sample error: ${err.message}`);
    } finally {
      setLoadingSample(false);
    }
  };

  // Job status polling
  useEffect(() => {
    if (!activeJob || (activeJob.status !== "pending" && activeJob.status !== "processing")) {
      return;
    }
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/jobs/${activeJob.job_id}`);
        if (res.ok) {
          const updated: JobStatus = await res.json();
          setActiveJob(updated);
        }
      } catch (err) {
        console.error("Poll job error:", err);
      }
    }, 400);

    return () => clearInterval(interval);
  }, [activeJob]);

  // Start background export job
  const handleStartExport = async (format: string) => {
    if (!videoPath) return;
    try {
      const res = await fetch("/api/convert", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_path: videoPath,
          export_format: format,
          config,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Export request failed");
      }
      const data = await res.json();
      setActiveJob({
        job_id: data.job_id,
        status: "pending",
        progress: 0.0,
        processed_frames: 0,
        total_frames: 0,
        error: null,
        output_available: false,
      });
    } catch (err: any) {
      alert(`Export error: ${err.message}`);
    }
  };

  // Cancel job
  const handleCancelJob = async (jobId: string) => {
    try {
      await fetch(`/api/jobs/${jobId}/cancel`, { method: "POST" });
      setActiveJob((prev) => (prev ? { ...prev, status: "cancelled" } : null));
    } catch (err) {
      console.error("Cancel job error:", err);
    }
  };

  return (
    <div className="app-container">
      <Header />

      <main className="main-content">
        {/* Left Column: Input, Preview, and Exports */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <UploadSection
            metadata={metadata}
            filename={filename}
            onUploadSuccess={(path, name, meta) => {
              setVideoPath(path);
              setFilename(name);
              setMetadata(meta);
              setTimestamp(0.0);
            }}
            onLoadSample={handleLoadSample}
            loading={loadingSample}
          />

          <PreviewSection
            preview={preview}
            metadata={metadata}
            timestamp={timestamp}
            onSeek={setTimestamp}
            loading={loadingPreview}
          />

          <ExportSection
            videoPath={videoPath}
            filename={filename}
            config={config}
            onStartExport={handleStartExport}
            onCancelJob={handleCancelJob}
            activeJob={activeJob}
          />
        </div>

        {/* Right Column: Settings Panel */}
        <div>
          <SettingsPanel
            config={config}
            onChange={setConfig}
            onReset={() => setConfig(DEFAULT_CONFIG)}
            ramps={ramps}
          />
        </div>
      </main>
    </div>
  );
};
