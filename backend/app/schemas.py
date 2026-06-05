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
