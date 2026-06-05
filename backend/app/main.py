from __future__ import annotations

import csv
import io
import json
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from send2trash import send2trash

from .config import AI_API_KEY, AI_BASE_URL, AI_MODEL, DEFAULT_OLLAMA_MODEL, save_ai_config
from .database import connect, init_db, json_tags, row_to_dict, utc_now
from .schemas import AIConfigUpdate, AnalyzeRequest, ItemListResponse, ItemUpdate, RunRequest, ScanRequest
from .services.ai_provider import analyze_with_ai, check_connection, is_configured
from .services.analyzer import analyze_text_rules, merge_ai_with_rules, to_update_dict
from .services.ocr import run_ocr
from .services.ollama import analyze_with_ollama, check_ollama
from .services.scanner import scan_directory


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="ScreenTextOrganizer", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_ocr_state: dict = {"running": False, "processed": 0, "failed": 0, "total": 0, "current_file": ""}
_ocr_lock = threading.Lock()


@app.get("/api/health")
def health() -> dict:
    ollama_info = check_ollama()
    ai_info = check_connection()
    return {
        "ok": True,
        "ollama_available": ollama_info["available"],
        "ollama_models": ollama_info.get("models", []),
        "ai_configured": is_configured(),
        "ai_available": ai_info.get("available", False),
        "ai_model": AI_MODEL,
        "ai_base_url": AI_BASE_URL,
    }


@app.get("/api/config/ai")
def get_ai_config() -> dict:
    """Return current AI config (key is masked)."""
    from .config import AI_API_KEY as key, AI_BASE_URL as url, AI_MODEL as model
    masked_key = ""
    if key:
        if len(key) > 8:
            masked_key = key[:4] + "*" * (len(key) - 8) + key[-4:]
        else:
            masked_key = "****"
    return {
        "api_key_masked": masked_key,
        "api_key_set": bool(key and key != "sk-your-api-key-here"),
        "base_url": url,
        "model": model,
    }


@app.post("/api/config/ai")
def update_ai_config(req: AIConfigUpdate) -> dict:
    """Save AI config to .env file."""
    save_ai_config(req.api_key, req.base_url, req.model)
    ai_info = check_connection()
    return {
        "saved": True,
        "ai_available": ai_info.get("available", False),
        **ai_info,
    }


@app.post("/api/ai/test")
def test_ai_config(req: AIConfigUpdate) -> dict:
    """Test AI config without saving it."""
    ai_info = check_connection(api_key=req.api_key, base_url=req.base_url, model=req.model)
    return {
        "ai_available": ai_info.get("available", False),
        **ai_info,
    }


@app.post("/api/scan")
def scan(req: ScanRequest) -> dict:
    try:
        return scan_directory(req.directory, req.recursive)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/items", response_model=ItemListResponse)
def list_items(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=200),
    status: str | None = None,
    category: str | None = None,
    suggestion: str | None = None,
    q: str | None = None,
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


def _ocr_worker(rows: list[dict]) -> None:
    global _ocr_state
    for row in rows:
        now = utc_now()
        with connect() as conn:
            conn.execute("UPDATE items SET ocr_status = ?, updated_at = ? WHERE id = ?", ("running", now, row["id"]))
        with _ocr_lock:
            _ocr_state["current_file"] = row.get("filename", "")
        try:
            text, confidence = run_ocr(row["source_path"])
            with connect() as conn:
                conn.execute(
                    "UPDATE items SET ocr_text = ?, ocr_confidence = ?, ocr_status = ?, ocr_error = NULL, updated_at = ? WHERE id = ?",
                    (text, confidence, "done", utc_now(), row["id"]),
                )
            with _ocr_lock:
                _ocr_state["processed"] += 1
        except Exception as exc:
            with connect() as conn:
                conn.execute(
                    "UPDATE items SET ocr_status = ?, ocr_error = ?, updated_at = ? WHERE id = ?",
                    ("failed", str(exc), utc_now(), row["id"]),
                )
            with _ocr_lock:
                _ocr_state["failed"] += 1
    with _ocr_lock:
        _ocr_state["running"] = False
        _ocr_state["current_file"] = ""


@app.post("/api/ocr/run")
def run_ocr_batch(req: RunRequest) -> dict:
    with _ocr_lock:
        if _ocr_state["running"]:
            return {"status": "already_running", **_ocr_state}

    with connect() as conn:
        sql = "SELECT id, source_path, filename FROM items WHERE ocr_status IN ('pending', 'failed') AND status != 'trashed' ORDER BY id"
        params: list[object] = []
        if req.limit:
            sql += " LIMIT ?"
            params.append(req.limit)
        rows = [dict(row) for row in conn.execute(sql, params).fetchall()]

    if not rows:
        return {"status": "idle", "processed": 0, "failed": 0, "total": 0, "current_file": ""}

    with _ocr_lock:
        _ocr_state.update({"running": True, "processed": 0, "failed": 0, "total": len(rows), "current_file": ""})

    thread = threading.Thread(target=_ocr_worker, args=(rows,), daemon=True)
    thread.start()
    return {"status": "started", **_ocr_state}


@app.get("/api/ocr/status")
def ocr_status() -> dict:
    with _ocr_lock:
        return {"status": "running" if _ocr_state["running"] else "idle", **_ocr_state}


@app.post("/api/analyze/run")
def run_analysis(req: AnalyzeRequest) -> dict:
    with connect() as conn:
        sql = """
            SELECT id, source_path, ocr_text
            FROM items
            WHERE status != 'trashed' AND COALESCE(ocr_text, '') != ''
            ORDER BY id
        """
        params: list[object] = []
        if req.limit:
            sql += " LIMIT ?"
            params.append(req.limit)
        rows = conn.execute(sql, params).fetchall()

    processed = 0
    ai_used = 0
    ollama_used = 0

    # Determine available providers
    env_configured = is_configured()
    ai_available = env_configured or bool(req.ai_api_key)
    ollama_info = check_ollama()
    ollama_available = ollama_info["available"]

    for row in rows:
        rules_result = analyze_text_rules(row["ocr_text"])
        result = None

        # Try providers based on preference
        provider = req.provider

        if provider == "auto":
            # Auto: try AI first, then Ollama, then rules
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
                ai_used += 1

        if result is None and provider in ("ai", "ollama", "auto") and ollama_available:
            ollama_result = analyze_with_ollama(
                row["ocr_text"],
                image_path=row["source_path"],
                include_image=req.include_image,
                model=req.model,
            )
            if ollama_result:
                result = merge_ai_with_rules(ollama_result, rules_result)
                ollama_used += 1

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
        processed += 1
    return {"processed": processed, "ai_used": ai_used, "ollama_used": ollama_used, "total": len(rows)}


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


@app.post("/api/items/{item_id}/trash")
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


@app.get("/api/export")
def export_items(format: Literal["json", "csv"] = "json") -> Response:
    with connect() as conn:
        rows = [row_to_dict(row) for row in conn.execute("SELECT * FROM items ORDER BY id").fetchall()]

    if format == "json":
        return Response(
            json.dumps(rows, ensure_ascii=False, indent=2),
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=pic-text-pull.json"},
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
