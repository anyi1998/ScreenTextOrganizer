from __future__ import annotations

import csv
import io
import json
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from send2trash import send2trash

from . import config
from .database import connect, init_db, json_tags, row_to_dict, utc_now
from .schemas import (
    AIConfigResponse,
    AIConfigSaveResponse,
    AIConfigUpdate,
    AIProviderCheckResponse,
    AnalyzeRequest,
    AnalyzeRunResponse,
    HealthResponse,
    ItemListResponse,
    ItemUpdate,
    OcrStatusResponse,
    RunRequest,
    ScanRequest,
    ScanResponse,
    StatsResponse,
    TasksStatusResponse,
    TrashResponse,
)
from .services.ai_provider import analyze_with_ai, check_connection, is_configured
from .services.analyzer import analyze_text_rules, merge_ai_with_rules, to_update_dict
from .services.ocr import run_ocr
from .services.ollama import analyze_with_ollama, check_ollama
from .services.scanner import scan_directory


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    with connect() as conn:
        conn.execute(
            """
            UPDATE items
            SET ocr_status = 'pending', updated_at = ?
            WHERE ocr_status = 'running'
            """,
            (utc_now(),),
        )
    yield


app = FastAPI(
    title="ScreenTextOrganizer",
    description="Local screenshot OCR and text organization API.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(config.CORS_ORIGINS),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    if config.SECURITY_HEADERS_ENABLED:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        if request.url.scheme == "https":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response

_ocr_state: dict[str, object] = {
    "running": False,
    "cancel_requested": False,
    "processed": 0,
    "failed": 0,
    "skipped": 0,
    "total": 0,
    "current_file": "",
    "started_at": None,
    "finished_at": None,
    "last_error": None,
}
_ocr_lock = threading.Lock()

_analysis_state: dict[str, object] = {
    "running": False,
    "cancel_requested": False,
    "processed": 0,
    "failed": 0,
    "skipped": 0,
    "ai_used": 0,
    "ollama_used": 0,
    "total": 0,
    "current_file": "",
    "started_at": None,
    "finished_at": None,
    "last_error": None,
}
_analysis_lock = threading.Lock()


def _ocr_status_name(state: dict[str, object]) -> str:
    if state["running"]:
        return "cancelling" if state["cancel_requested"] else "running"
    if state["cancel_requested"]:
        return "cancelled"
    return "idle"


def _ocr_snapshot() -> dict:
    with _ocr_lock:
        state = dict(_ocr_state)
    return {"status": _ocr_status_name(state), **state}


def _analysis_status_name(state: dict[str, object]) -> str:
    if state["running"]:
        return "cancelling" if state["cancel_requested"] else "running"
    if state["cancel_requested"]:
        return "cancelled"
    return "idle"


def _analysis_snapshot() -> dict:
    with _analysis_lock:
        state = dict(_analysis_state)
    return {"status": _analysis_status_name(state), **state}


def _tasks_snapshot() -> dict:
    ocr = _ocr_snapshot()
    analysis = _analysis_snapshot()
    active_task = None
    if ocr["running"]:
        active_task = "ocr"
    elif analysis["running"]:
        active_task = "analysis"
    return {
        "busy": active_task is not None,
        "active_task": active_task,
        "ocr": ocr,
        "analysis": analysis,
    }


def _mask_api_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


def _count_buckets(conn, column: str) -> list[dict[str, object]]:
    rows = conn.execute(
        f"""
        SELECT COALESCE({column}, 'none') AS name, COUNT(*) AS count
        FROM items
        GROUP BY COALESCE({column}, 'none')
        ORDER BY count DESC, name ASC
        """
    ).fetchall()
    return [{"name": row["name"], "count": row["count"]} for row in rows]


@app.get("/api/health", response_model=HealthResponse)
def health() -> dict:
    ollama_info = check_ollama()
    ai_info = check_connection()
    return {
        "ok": True,
        "environment": config.APP_ENV,
        "data_dir": str(config.DATA_DIR),
        "database_path": str(config.DB_PATH),
        "ollama_available": ollama_info["available"],
        "ollama_models": ollama_info.get("models", []),
        "ai_configured": is_configured(),
        "ai_available": ai_info.get("available", False),
        "ai_model": config.AI_MODEL,
        "ai_base_url": config.AI_BASE_URL,
    }


@app.get("/api/tasks/status", response_model=TasksStatusResponse)
def tasks_status() -> dict:
    return _tasks_snapshot()


@app.get("/api/config/ai", response_model=AIConfigResponse)
def get_ai_config() -> dict:
    """Return current AI config (key is masked)."""
    return {
        "api_key_masked": _mask_api_key(config.AI_API_KEY),
        "api_key_set": bool(config.AI_API_KEY and config.AI_API_KEY != "sk-your-api-key-here"),
        "base_url": config.AI_BASE_URL,
        "model": config.AI_MODEL,
    }


@app.post("/api/config/ai", response_model=AIConfigSaveResponse)
def update_ai_config(req: AIConfigUpdate) -> dict:
    """Save AI config to .env file."""
    config.save_ai_config(req.api_key, req.base_url, req.model, clear_api_key=req.clear_api_key)
    ai_info = check_connection()
    return {
        "saved": True,
        "ai_available": ai_info.get("available", False),
        **ai_info,
    }


@app.post("/api/ai/test", response_model=AIProviderCheckResponse)
def test_ai_config(req: AIConfigUpdate) -> dict:
    """Test AI config without saving it."""
    ai_info = check_connection(api_key=req.api_key, base_url=req.base_url, model=req.model)
    return {
        "ai_available": ai_info.get("available", False),
        **ai_info,
    }


@app.post("/api/scan", response_model=ScanResponse)
def scan(req: ScanRequest) -> dict:
    try:
        return scan_directory(req.directory, req.recursive)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/items", response_model=ItemListResponse)
def list_items(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=200),
    status: Literal["unreviewed", "kept", "review", "trashed"] | None = None,
    category: str | None = Query(default=None, max_length=80),
    suggestion: Literal["keep", "review", "delete"] | None = None,
    q: str | None = Query(default=None, max_length=200),
) -> dict:
    filters: list[str] = []
    params: list[object] = []
    if status:
        filters.append("status = ?")
        params.append(status)
    if category:
        filters.append("category = ?")
        params.append(category)
    if suggestion:
        filters.append("keep_suggestion = ?")
        params.append(suggestion)
    if q:
        filters.append("(filename LIKE ? OR ocr_text LIKE ? OR summary LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like])

    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    offset = (page - 1) * page_size
    with connect() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS count FROM items {where}", params).fetchone()["count"]
        rows = conn.execute(
            f"""
            SELECT * FROM items
            {where}
            ORDER BY updated_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, offset],
        ).fetchall()
    return {"items": [row_to_dict(row) for row in rows], "total": total, "page": page, "page_size": page_size}


@app.get("/api/stats", response_model=StatsResponse)
def stats() -> dict:
    with connect() as conn:
        totals = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(file_size), 0) AS storage_bytes,
                SUM(CASE WHEN status = 'review' OR keep_suggestion = 'review' THEN 1 ELSE 0 END) AS review_queue,
                SUM(CASE WHEN ocr_status = 'done' THEN 1 ELSE 0 END) AS done_ocr,
                SUM(CASE WHEN ocr_status IN ('pending', 'running') THEN 1 ELSE 0 END) AS pending_ocr,
                SUM(CASE WHEN ocr_status = 'failed' THEN 1 ELSE 0 END) AS failed_ocr,
                SUM(CASE WHEN analysis_source IS NOT NULL THEN 1 ELSE 0 END) AS analyzed,
                SUM(CASE WHEN keep_suggestion = 'keep' THEN 1 ELSE 0 END) AS keep_suggestion_keep,
                SUM(CASE WHEN keep_suggestion = 'review' THEN 1 ELSE 0 END) AS keep_suggestion_review,
                SUM(CASE WHEN keep_suggestion = 'delete' THEN 1 ELSE 0 END) AS keep_suggestion_delete
            FROM items
            """
        ).fetchone()
        return {
            "total": totals["total"] or 0,
            "storage_bytes": totals["storage_bytes"] or 0,
            "review_queue": totals["review_queue"] or 0,
            "done_ocr": totals["done_ocr"] or 0,
            "pending_ocr": totals["pending_ocr"] or 0,
            "failed_ocr": totals["failed_ocr"] or 0,
            "analyzed": totals["analyzed"] or 0,
            "keep_suggestion_keep": totals["keep_suggestion_keep"] or 0,
            "keep_suggestion_review": totals["keep_suggestion_review"] or 0,
            "keep_suggestion_delete": totals["keep_suggestion_delete"] or 0,
            "by_status": _count_buckets(conn, "status"),
            "by_ocr_status": _count_buckets(conn, "ocr_status"),
            "by_suggestion": _count_buckets(conn, "keep_suggestion"),
            "by_analysis_source": _count_buckets(conn, "analysis_source"),
        }


def _ocr_worker(rows: list[dict]) -> None:
    try:
        for index, row in enumerate(rows):
            with _ocr_lock:
                if _ocr_state["cancel_requested"]:
                    _ocr_state["skipped"] = int(_ocr_state["skipped"]) + len(rows) - index
                    break
                _ocr_state["current_file"] = row.get("filename", "")

            now = utc_now()
            with connect() as conn:
                conn.execute(
                    "UPDATE items SET ocr_status = ?, updated_at = ? WHERE id = ?",
                    ("running", now, row["id"]),
                )

            try:
                text, confidence = run_ocr(row["source_path"])
                with connect() as conn:
                    conn.execute(
                        """
                        UPDATE items
                        SET ocr_text = ?, ocr_confidence = ?, ocr_status = ?,
                            ocr_error = NULL, updated_at = ?
                        WHERE id = ?
                        """,
                        (text, confidence, "done", utc_now(), row["id"]),
                    )
                with _ocr_lock:
                    _ocr_state["processed"] = int(_ocr_state["processed"]) + 1
            except Exception as exc:
                with connect() as conn:
                    conn.execute(
                        "UPDATE items SET ocr_status = ?, ocr_error = ?, updated_at = ? WHERE id = ?",
                        ("failed", str(exc), utc_now(), row["id"]),
                    )
                with _ocr_lock:
                    _ocr_state["failed"] = int(_ocr_state["failed"]) + 1
                    _ocr_state["last_error"] = str(exc)
    finally:
        with _ocr_lock:
            _ocr_state["running"] = False
            _ocr_state["current_file"] = ""
            _ocr_state["finished_at"] = utc_now()


@app.post("/api/ocr/run", response_model=OcrStatusResponse)
def run_ocr_batch(req: RunRequest) -> dict:
    with _ocr_lock:
        if _ocr_state["running"]:
            return {"status": "already_running", **dict(_ocr_state)}
    with _analysis_lock:
        if _analysis_state["running"]:
            raise HTTPException(status_code=409, detail="Analysis is already running")

    with connect() as conn:
        sql = "SELECT id, source_path, filename FROM items WHERE ocr_status IN ('pending', 'failed') AND status != 'trashed' ORDER BY id"
        params: list[object] = []
        if req.limit:
            sql += " LIMIT ?"
            params.append(req.limit)
        rows = [dict(row) for row in conn.execute(sql, params).fetchall()]

    if not rows:
        with _ocr_lock:
            _ocr_state.update(
                {
                    "running": False,
                    "cancel_requested": False,
                    "processed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "total": 0,
                    "current_file": "",
                    "started_at": None,
                    "finished_at": utc_now(),
                    "last_error": None,
                }
            )
        return _ocr_snapshot()

    with _ocr_lock:
        _ocr_state.update(
            {
                "running": True,
                "cancel_requested": False,
                "processed": 0,
                "failed": 0,
                "skipped": 0,
                "total": len(rows),
                "current_file": "",
                "started_at": utc_now(),
                "finished_at": None,
                "last_error": None,
            }
        )

    thread = threading.Thread(target=_ocr_worker, args=(rows,), daemon=True)
    thread.start()
    with _ocr_lock:
        return {"status": "started", **dict(_ocr_state)}


@app.get("/api/ocr/status", response_model=OcrStatusResponse)
def ocr_status() -> dict:
    return _ocr_snapshot()


@app.post("/api/ocr/cancel", response_model=OcrStatusResponse)
def cancel_ocr() -> dict:
    with _ocr_lock:
        if _ocr_state["running"]:
            _ocr_state["cancel_requested"] = True
    return _ocr_snapshot()


def _analyze_one(row: dict, req: AnalyzeRequest, ai_available: bool, ollama_available: bool) -> tuple[int, int]:
    rules_result = analyze_text_rules(row["ocr_text"])
    result = None
    ai_used = 0
    ollama_used = 0
    provider = req.provider

    if provider == "auto":
        if ai_available:
            provider = "ai"
        elif ollama_available:
            provider = "ollama"
        else:
            provider = "rules"

    if provider == "ai" and ai_available:
        ai_result = analyze_with_ai(
            row["ocr_text"],
            api_key=req.ai_api_key,
            base_url=req.ai_base_url,
            model=req.ai_model,
        )
        if ai_result:
            result = merge_ai_with_rules(ai_result, rules_result)
            ai_used = 1

    if result is None and provider in ("ai", "ollama", "auto") and ollama_available:
        ollama_result = analyze_with_ollama(
            row["ocr_text"],
            image_path=row["source_path"],
            include_image=req.include_image,
            model=req.model,
        )
        if ollama_result:
            result = merge_ai_with_rules(ollama_result, rules_result)
            ollama_used = 1

    if result is None:
        result = rules_result

    update = to_update_dict(result)
    with connect() as conn:
        conn.execute(
            """
            UPDATE items
            SET analysis_source = ?, category = ?, summary = ?, value_score = ?,
                keep_suggestion = ?, staleness_risk = ?, distortion_risk = ?,
                tags = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                update["analysis_source"],
                update["category"],
                update["summary"],
                update["value_score"],
                update["keep_suggestion"],
                update["staleness_risk"],
                update["distortion_risk"],
                update["tags"],
                utc_now(),
                row["id"],
            ),
        )
    return ai_used, ollama_used


def _analysis_worker(rows: list[dict], req: AnalyzeRequest) -> None:
    ai_available = is_configured() or bool(req.ai_api_key)
    ollama_available = check_ollama()["available"]

    try:
        for index, row in enumerate(rows):
            with _analysis_lock:
                if _analysis_state["cancel_requested"]:
                    _analysis_state["skipped"] = int(_analysis_state["skipped"]) + len(rows) - index
                    break
                _analysis_state["current_file"] = row.get("filename", "")

            try:
                ai_used, ollama_used = _analyze_one(row, req, ai_available, ollama_available)
                with _analysis_lock:
                    _analysis_state["processed"] = int(_analysis_state["processed"]) + 1
                    _analysis_state["ai_used"] = int(_analysis_state["ai_used"]) + ai_used
                    _analysis_state["ollama_used"] = int(_analysis_state["ollama_used"]) + ollama_used
            except Exception as exc:
                with _analysis_lock:
                    _analysis_state["failed"] = int(_analysis_state["failed"]) + 1
                    _analysis_state["last_error"] = str(exc)
    finally:
        with _analysis_lock:
            _analysis_state["running"] = False
            _analysis_state["current_file"] = ""
            _analysis_state["finished_at"] = utc_now()


@app.post("/api/analyze/run", response_model=AnalyzeRunResponse)
def run_analysis(req: AnalyzeRequest) -> dict:
    with _analysis_lock:
        if _analysis_state["running"]:
            return {"status": "already_running", **dict(_analysis_state)}
    with _ocr_lock:
        if _ocr_state["running"]:
            raise HTTPException(status_code=409, detail="OCR is already running")

    with connect() as conn:
        sql = """
            SELECT id, source_path, filename, ocr_text
            FROM items
            WHERE status != 'trashed' AND COALESCE(ocr_text, '') != ''
            ORDER BY id
        """
        params: list[object] = []
        if req.limit:
            sql += " LIMIT ?"
            params.append(req.limit)
        rows = [dict(row) for row in conn.execute(sql, params).fetchall()]

    if not rows:
        with _analysis_lock:
            _analysis_state.update(
                {
                    "running": False,
                    "cancel_requested": False,
                    "processed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "ai_used": 0,
                    "ollama_used": 0,
                    "total": 0,
                    "current_file": "",
                    "started_at": None,
                    "finished_at": utc_now(),
                    "last_error": None,
                }
            )
        return _analysis_snapshot()

    with _analysis_lock:
        _analysis_state.update(
            {
                "running": True,
                "cancel_requested": False,
                "processed": 0,
                "failed": 0,
                "skipped": 0,
                "ai_used": 0,
                "ollama_used": 0,
                "total": len(rows),
                "current_file": "",
                "started_at": utc_now(),
                "finished_at": None,
                "last_error": None,
            }
        )

    thread = threading.Thread(target=_analysis_worker, args=(rows, req), daemon=True)
    thread.start()
    with _analysis_lock:
        return {"status": "started", **dict(_analysis_state)}


@app.get("/api/analyze/status", response_model=AnalyzeRunResponse)
def analysis_status() -> dict:
    return _analysis_snapshot()


@app.post("/api/analyze/cancel", response_model=AnalyzeRunResponse)
def cancel_analysis() -> dict:
    with _analysis_lock:
        if _analysis_state["running"]:
            _analysis_state["cancel_requested"] = True
    return _analysis_snapshot()


@app.patch("/api/items/{item_id}")
def update_item(item_id: int, update: ItemUpdate) -> dict:
    fields: list[str] = []
    params: list[object] = []
    if update.status is not None:
        fields.append("status = ?")
        params.append(update.status)
    if update.notes is not None:
        fields.append("notes = ?")
        params.append(update.notes)
    if update.ocr_text is not None:
        fields.append("ocr_text = ?")
        params.append(update.ocr_text)
        fields.extend(
            [
                "analysis_source = NULL",
                "category = NULL",
                "summary = NULL",
                "value_score = NULL",
                "keep_suggestion = NULL",
                "staleness_risk = NULL",
                "distortion_risk = NULL",
            ]
        )
    if update.tags is not None:
        fields.append("tags = ?")
        params.append(json_tags(update.tags))
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    fields.append("updated_at = ?")
    params.append(utc_now())
    params.append(item_id)

    with connect() as conn:
        cur = conn.execute(f"UPDATE items SET {', '.join(fields)} WHERE id = ?", params)
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Item not found")
        row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    return row_to_dict(row)


@app.post("/api/items/{item_id}/trash", response_model=TrashResponse)
def trash_item(item_id: int) -> dict:
    with connect() as conn:
        row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")

    try:
        send2trash(row["source_path"])
        with connect() as conn:
            conn.execute(
                """
                UPDATE items
                SET status = 'trashed', trashed_at = ?, trash_error = NULL, updated_at = ?
                WHERE id = ?
                """,
                (utc_now(), utc_now(), item_id),
            )
        return {"ok": True}
    except Exception as exc:
        with connect() as conn:
            conn.execute(
                "UPDATE items SET trash_error = ?, updated_at = ? WHERE id = ?",
                (str(exc), utc_now(), item_id),
            )
        raise HTTPException(status_code=500, detail=f"Move to recycle bin failed: {exc}") from exc


@app.get("/api/items/{item_id}/image")
def get_image(item_id: int) -> FileResponse:
    row = get_existing_item(item_id)
    path = Path(row["source_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Source image not found")
    return FileResponse(path)


@app.get("/api/items/{item_id}/thumbnail")
def get_thumbnail(item_id: int) -> FileResponse:
    row = get_existing_item(item_id)
    path = Path(row["thumbnail_path"] or "")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return FileResponse(path, media_type="image/jpeg")


def _markdown_inline(value: object) -> str:
    if value is None:
        return "-"
    text = str(value).replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return "-"
    return text.replace("|", "\\|").replace("\n", "<br>")


def _markdown_heading(value: object) -> str:
    text = str(value or "Untitled").replace("\r\n", " ").replace("\r", " ").replace("\n", " ").strip()
    return text or "Untitled"


def _markdown_code_block(text: object) -> str:
    content = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not content:
        return "_No text._"

    longest_backtick_run = 0
    current_run = 0
    for char in content:
        if char == "`":
            current_run += 1
            longest_backtick_run = max(longest_backtick_run, current_run)
        else:
            current_run = 0
    fence = "`" * max(3, longest_backtick_run + 1)
    return f"{fence}text\n{content}\n{fence}"


def _render_markdown_export(rows: list[dict]) -> str:
    lines = [
        "# ScreenTextOrganizer Export",
        "",
        f"- Generated: {utc_now()}",
        f"- Items: {len(rows)}",
        "",
    ]

    for row in rows:
        tags = row.get("tags") or []
        if not isinstance(tags, list):
            tags = []
        tag_text = ", ".join(str(tag) for tag in tags) if tags else "-"
        score = row.get("value_score")

        lines.extend(
            [
                f"## {_markdown_heading(row.get('filename'))}",
                "",
                "| Field | Value |",
                "| --- | --- |",
                f"| ID | {_markdown_inline(row.get('id'))} |",
                f"| Source | {_markdown_inline(row.get('source_path'))} |",
                f"| Status | {_markdown_inline(row.get('status'))} |",
                f"| OCR Status | {_markdown_inline(row.get('ocr_status'))} |",
                f"| Suggestion | {_markdown_inline(row.get('keep_suggestion'))} |",
                f"| Score | {_markdown_inline(score if score is not None else '-')} |",
                f"| Category | {_markdown_inline(row.get('category'))} |",
                f"| Staleness Risk | {_markdown_inline(row.get('staleness_risk'))} |",
                f"| Distortion Risk | {_markdown_inline(row.get('distortion_risk'))} |",
                f"| Tags | {_markdown_inline(tag_text)} |",
                "",
                "### Summary",
                "",
                _markdown_inline(row.get("summary")),
                "",
                "### OCR Text",
                "",
                _markdown_code_block(row.get("ocr_text")),
                "",
            ]
        )

        notes = str(row.get("notes") or "").strip()
        if notes:
            lines.extend(["### Notes", "", _markdown_code_block(notes), ""])

    return "\n".join(lines).rstrip() + "\n"


@app.get("/api/export")
def export_items(format: Literal["json", "csv", "markdown"] = "json") -> Response:
    with connect() as conn:
        rows = [row_to_dict(row) for row in conn.execute("SELECT * FROM items ORDER BY id").fetchall()]

    if format == "json":
        return Response(
            json.dumps(rows, ensure_ascii=False, indent=2),
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=pic-text-pull.json"},
        )

    if format == "markdown":
        return Response(
            _render_markdown_export(rows),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=pic-text-pull.md"},
        )

    buffer = io.StringIO()
    if rows:
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            csv_row = {**row, "tags": json.dumps(row.get("tags", []), ensure_ascii=False)}
            writer.writerow(csv_row)
    return Response(
        buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=pic-text-pull.csv"},
    )


# Serve frontend static files in production
_frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _frontend_dist.is_dir():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")


def get_existing_item(item_id: int) -> dict:
    with connect() as conn:
        row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")
    return row_to_dict(row)
