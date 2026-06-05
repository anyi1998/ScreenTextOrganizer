import type { AIConfig, HealthInfo, ListResponse, OcrStatus, PicItem } from "./types";

const API_BASE = import.meta.env.VITE_API_URL || "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function healthCheck() {
  return request<HealthInfo>("/api/health");
}

export function getAIConfig() {
  return request<AIConfig>("/api/config/ai");
}

export function saveAIConfig(config: { api_key: string; base_url: string; model: string }) {
  return request<{ saved: boolean; ai_available: boolean }>("/api/config/ai", {
    method: "POST",
    body: JSON.stringify(config)
  });
}

export function testAIConfig(config: { api_key: string; base_url: string; model: string }) {
  return request<{ ai_available: boolean }>("/api/ai/test", {
    method: "POST",
    body: JSON.stringify(config)
  });
}

export function listItems(params: URLSearchParams) {
  return request<ListResponse>(`/api/items?${params.toString()}`);
}

export function scan(directory: string, recursive: boolean) {
  return request<Record<string, unknown>>("/api/scan", {
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

export function runAnalysis(options: {
  limit?: number;
  provider: string;
  include_image: boolean;
  model?: string;
  ai_api_key?: string;
  ai_base_url?: string;
  ai_model?: string;
}) {
  return request<Record<string, number>>("/api/analyze/run", {
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
