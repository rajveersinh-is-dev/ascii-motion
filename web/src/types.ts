export type ResolutionPreset = "low" | "medium" | "high" | "ultra" | "custom";
export type ColorStyle = "monochrome" | "color" | "green" | "amber" | "custom";
export type DitherMode = "none" | "bayer" | "floyd_steinberg";
export type EdgeMode = "none" | "sobel";

export interface VideoMetadata {
  width: number;
  height: number;
  duration: number;
  fps: number;
  total_frames: number;
  has_audio: boolean;
  video_codec: string | null;
  audio_codec: string | null;
}

export interface RenderConfig {
  preset: ResolutionPreset;
  width: number;
  height: number | null;
  char_aspect_ratio: number;
  target_fps: number | null;
  trim_start: number;
  trim_end: number | null;
  max_duration: number | null;
  max_frames: number | null;
  brightness: number;
  contrast: number;
  gamma: number;
  invert: boolean;
  ramp_name: string;
  custom_ramp: string | null;
  style: ColorStyle;
  foreground_color: string;
  background_color: string;
  dithering: DitherMode;
  edge_mode: EdgeMode;
  edge_strength: number;
  temporal_smoothing: number;
}

export interface PreviewData {
  width: number;
  height: number;
  lines: string[];
  colors: string[][] | null;
  style: string;
  background_color: string;
  foreground_color: string;
}

export interface JobStatus {
  job_id: string;
  status: "pending" | "processing" | "completed" | "failed" | "cancelled";
  progress: number;
  processed_frames: number;
  total_frames: number;
  error: string | null;
  output_available: boolean;
}
