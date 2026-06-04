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
  category: string | null;
  summary: string | null;
  value_score: number | null;
  keep_suggestion: string | null;
  staleness_risk: string | null;
  distortion_risk: string | null;
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

