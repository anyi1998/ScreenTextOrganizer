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

export interface ScanError {
  file: string;
  error: string;
}

export interface ScanResult {
  scanned: number;
  inserted: number;
  updated: number;
  unchanged: number;
  failed: number;
  errors: ScanError[];
}

export interface AnalyzeResult {
  status: "idle" | "running" | "started" | "already_running" | "cancelling" | "cancelled";
  running: boolean;
  cancel_requested: boolean;
  processed: number;
  failed: number;
  skipped: number;
  ai_used: number;
  ollama_used: number;
  total: number;
  current_file: string;
  started_at: string | null;
  finished_at: string | null;
  last_error: string | null;
}

export interface StatsBucket {
  name: string;
  count: number;
}

export interface StatsInfo {
  total: number;
  storage_bytes: number;
  review_queue: number;
  done_ocr: number;
  pending_ocr: number;
  failed_ocr: number;
  analyzed: number;
  keep_suggestion_keep: number;
  keep_suggestion_review: number;
  keep_suggestion_delete: number;
  by_status: StatsBucket[];
  by_ocr_status: StatsBucket[];
  by_suggestion: StatsBucket[];
  by_analysis_source: StatsBucket[];
}

export interface OcrStatus {
  status: "idle" | "running" | "started" | "already_running" | "cancelling" | "cancelled";
  running: boolean;
  cancel_requested: boolean;
  processed: number;
  failed: number;
  skipped: number;
  total: number;
  current_file: string;
  started_at: string | null;
  finished_at: string | null;
  last_error: string | null;
}

export interface HealthInfo {
  ok: boolean;
  environment: string;
  data_dir: string;
  database_path: string;
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

export interface AIConfigUpdate {
  api_key: string;
  base_url: string;
  model: string;
  clear_api_key?: boolean;
}
