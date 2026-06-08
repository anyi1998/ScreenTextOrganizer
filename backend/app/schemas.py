from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    directory: str
    recursive: bool = True


class RunRequest(BaseModel):
    limit: int | None = Field(default=None, ge=1, le=500)


class AnalyzeRequest(BaseModel):
    limit: int | None = Field(default=None, ge=1, le=500)
    provider: Literal["auto", "ai", "ollama", "rules"] = "auto"
    include_image: bool = False
    model: str | None = None
    ai_api_key: str | None = None
    ai_base_url: str | None = None
    ai_model: str | None = None


class AIConfigUpdate(BaseModel):
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    clear_api_key: bool = False


class HealthResponse(BaseModel):
    ok: bool
    environment: str
    data_dir: str
    database_path: str
    ollama_available: bool
    ollama_models: list[str]
    ai_configured: bool
    ai_available: bool
    ai_model: str
    ai_base_url: str


class AIConfigResponse(BaseModel):
    api_key_masked: str
    api_key_set: bool
    base_url: str
    model: str


class AIProviderCheckResponse(BaseModel):
    ai_available: bool
    available: bool
    reason: str | None = None
    model: str | None = None
    base_url: str | None = None
    models_found: int | None = None


class AIConfigSaveResponse(AIProviderCheckResponse):
    saved: bool


class ScanError(BaseModel):
    file: str
    error: str


class ScanResponse(BaseModel):
    scanned: int
    inserted: int
    updated: int
    unchanged: int
    failed: int
    errors: list[ScanError]


class OcrStatusResponse(BaseModel):
    status: Literal["idle", "running", "started", "already_running", "cancelling", "cancelled"]
    running: bool
    cancel_requested: bool
    processed: int
    failed: int
    skipped: int
    total: int
    current_file: str
    started_at: str | None
    finished_at: str | None
    last_error: str | None


class AnalyzeRunResponse(BaseModel):
    status: Literal["idle", "running", "started", "already_running", "cancelling", "cancelled"]
    running: bool
    cancel_requested: bool
    processed: int
    failed: int
    skipped: int
    ai_used: int
    ollama_used: int
    total: int
    current_file: str
    started_at: str | None
    finished_at: str | None
    last_error: str | None


class TasksStatusResponse(BaseModel):
    busy: bool
    active_task: Literal["ocr", "analysis"] | None
    ocr: OcrStatusResponse
    analysis: AnalyzeRunResponse


class StatsBucket(BaseModel):
    name: str
    count: int


class StatsResponse(BaseModel):
    total: int
    storage_bytes: int
    review_queue: int
    done_ocr: int
    pending_ocr: int
    failed_ocr: int
    analyzed: int
    keep_suggestion_keep: int
    keep_suggestion_review: int
    keep_suggestion_delete: int
    by_status: list[StatsBucket]
    by_ocr_status: list[StatsBucket]
    by_suggestion: list[StatsBucket]
    by_analysis_source: list[StatsBucket]


class TrashResponse(BaseModel):
    ok: bool


class ItemUpdate(BaseModel):
    status: Literal["unreviewed", "kept", "review", "trashed"] | None = None
    notes: str | None = None
    ocr_text: str | None = None
    tags: list[str] | None = None


class ItemListResponse(BaseModel):
    items: list[dict]
    total: int
    page: int
    page_size: int
