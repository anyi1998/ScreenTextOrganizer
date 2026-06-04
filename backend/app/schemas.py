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
    use_ollama: bool = False
    include_image: bool = False
    model: str | None = None


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

