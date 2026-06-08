import type {
  AIConfig,
  AIConfigUpdate,
  AnalyzeResult,
  HealthInfo,
  ListResponse,
  OcrStatus,
  PicItem,
  ScanResult,
  StatsInfo
} from "./types";

const API_BASE = import.meta.env.VITE_API_URL || "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init
  });
  if (!res.ok) {
    throw new Error(await readErrorMessage(res));
  }
  return res.json() as Promise<T>;
}

async function readErrorMessage(res: Response) {
  const text = await res.text();
  if (!text) return `HTTP ${res.status}`;
  try {
    const data = JSON.parse(text) as { detail?: unknown; message?: unknown };
    const detail = data.detail ?? data.message;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((entry) => {
          if (entry && typeof entry === "object" && "msg" in entry) {
            return String((entry as { msg: unknown }).msg);
          }
          return String(entry);
        })
        .join("; ");
    }
    if (detail) return JSON.stringify(detail);
  } catch {
    // Fall through to the raw response body.
  }
  return text;
}

export function healthCheck() {
  return request<HealthInfo>("/api/health");
}

export function getAIConfig() {
  return request<AIConfig>("/api/config/ai");
}

export function saveAIConfig(config: AIConfigUpdate) {
  return request<{ saved: boolean; ai_available: boolean }>("/api/config/ai", {
    method: "POST",
    body: JSON.stringify(config)
  });
}

export function testAIConfig(config: AIConfigUpdate) {
  return request<{ ai_available: boolean }>("/api/ai/test", {
    method: "POST",
    body: JSON.stringify(config)
  });
}

export function listItems(params: URLSearchParams) {
  return request<ListResponse>(`/api/items?${params.toString()}`);
}

export function getStats() {
  return request<StatsInfo>("/api/stats");
}

export function scan(directory: string, recursive: boolean) {
  return request<ScanResult>("/api/scan", {
    method: "POST",
    body: JSON.stringify({ directory, recursive })
  });
}

export function runOcr(limit?: number) {
  return request<OcrStatus>("/api/ocr/run", {
    method: "POST",
    body: JSON.stringify({ limit: limit || null })
  });
}

export function getOcrStatus() {
  return request<OcrStatus>("/api/ocr/status");
}

export function cancelOcr() {
  return request<OcrStatus>("/api/ocr/cancel", { method: "POST" });
}

export function runAnalysis(options: {
  limit?: number;
  provider: string;
  include_image: boolean;
  model?: string;
  ai_api_key?: string;
  ai_base_url?: string;
  ai_model?: string;
}) {
  return request<AnalyzeResult>("/api/analyze/run", {
    method: "POST",
    body: JSON.stringify({
      limit: options.limit || null,
      provider: options.provider,
      include_image: options.include_image,
      model: options.model || null,
      ai_api_key: options.ai_api_key || null,
      ai_base_url: options.ai_base_url || null,
      ai_model: options.ai_model || null
    })
  });
}

export function getAnalysisStatus() {
  return request<AnalyzeResult>("/api/analyze/status");
}

export function cancelAnalysis() {
  return request<AnalyzeResult>("/api/analyze/cancel", { method: "POST" });
}

export function updateItem(id: number, body: Partial<Pick<PicItem, "status" | "notes" | "ocr_text" | "tags">>) {
  return request<PicItem>(`/api/items/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body)
  });
}

export function trashItem(id: number) {
  return request<{ ok: boolean }>(`/api/items/${id}/trash`, { method: "POST" });
}

export function imageUrl(id: number) {
  return `${API_BASE}/api/items/${id}/image`;
}

export function thumbnailUrl(id: number) {
  return `${API_BASE}/api/items/${id}/thumbnail`;
}

export function exportUrl(format: "json" | "csv") {
  return `${API_BASE}/api/export?format=${format}`;
}
