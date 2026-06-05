export type ItemStatus = "unreviewed" | "kept" | "review" | "trashed";

export interface PicItem {
  id: number;
  source_path: string;
  filename: string;
  file_hash: string;
  file_size: number;
  width: number | null;
  height: number | null;
  created_time: string | null;
  modified_time: string | null;
  thumbnail_path: string | null;
  ocr_text: string;
  ocr_confidence: number | null;
  ocr_status: string;
  ocr_error: string | null;
  analysis_source: string | null;
  category: string | null;       // keep_reason
  summary: string | null;
  value_score: number | null;
  keep_suggestion: string | null;
  staleness_risk: string | null;  // topic
  distortion_risk: string | null; // ocr_quality
  tags: string[];
  status: ItemStatus;
  notes: string;
  updated_at: string;
  trashed_at: string | null;
  trash_error: string | null;
}

export interface ListResponse {
  items: PicItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface OcrStatus {
  status: "idle" | "running" | "started" | "already_running";
  running: boolean;
  processed: number;
  failed: number;
  total: number;
  current_file: string;
}

export interface HealthInfo {
  ok: boolean;
  ollama_available: boolean;
  ollama_models: string[];
  ai_configured: boolean;
  ai_available: boolean;
  ai_model: string;
  ai_base_url: string;
}

export interface AIConfig {
  api_key_masked: string;
  api_key_set: boolean;
  base_url: string;
  model: string;
}
