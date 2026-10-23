import React, { useRef, useState } from "react";
import { VideoMetadata } from "../types";

interface UploadSectionProps {
  metadata: VideoMetadata | null;
  filename: string | null;
  onUploadSuccess: (videoPath: string, filename: string, meta: VideoMetadata) => void;
  onLoadSample: () => void;
  loading: boolean;
}

export const UploadSection: React.FC<UploadSectionProps> = ({
  metadata,
  filename,
  onUploadSuccess,
  onLoadSample,
  loading,
}) => {
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const uploadFile = async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Upload failed");
      }
      const data = await res.json();
      onUploadSuccess(data.path, data.filename, data.metadata);
    } catch (err: any) {
      alert(`Upload error: ${err.message}`);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      uploadFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">Video Input & Metadata</span>
        <button
          className="btn btn-secondary btn-sm"
          onClick={onLoadSample}
          disabled={loading}
        >
          {loading ? "Loading Sample..." : "Use Sample Demo Video"}
        </button>
      </div>

      <div
        className={`dropzone ${dragActive ? "active" : ""}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="video/*,.mp4,.mov,.webm,.avi,.mkv"
          style={{ display: "none" }}
          onChange={(e) => {
            if (e.target.files && e.target.files[0]) {
              uploadFile(e.target.files[0]);
            }
          }}
        />
        <div className="dropzone-icon">⤓</div>
        <div className="dropzone-title">
          {filename ? `Current: ${filename}` : "Drag and drop video here, or click to browse"}
        </div>
        <div className="dropzone-hint">
          Supports MP4, MOV, WebM, AVI, MKV (H.264, VP9, AV1, ProRes)
        </div>
      </div>

      {metadata && (
        <div className="badge-group">
          <div className="meta-badge">
            Resolution: <span>{metadata.width}x{metadata.height}</span>
          </div>
          <div className="meta-badge">
            Duration: <span>{metadata.duration.toFixed(2)}s</span>
          </div>
          <div className="meta-badge">
            FPS: <span>{metadata.fps.toFixed(1)}</span>
          </div>
          <div className="meta-badge">
            Frames: <span>{metadata.total_frames}</span>
          </div>
          <div className="meta-badge">
            Codec: <span>{metadata.video_codec || "unknown"}</span>
          </div>
          <div className="meta-badge">
            Audio: <span>{metadata.has_audio ? metadata.audio_codec || "yes" : "none"}</span>
          </div>
        </div>
      )}
    </div>
  );
};
