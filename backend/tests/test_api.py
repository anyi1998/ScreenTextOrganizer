from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.database import connect, utc_now
from app.main import _analysis_lock, _analysis_state, _ocr_lock, _ocr_state, app


def test_health():
    with TestClient(app) as client:
        res = client.get("/api/health")

    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["environment"] in {"development", "test", "production"}
    assert data["data_dir"]
    assert data["database_path"]
    assert res.headers["x-content-type-options"] == "nosniff"


def test_scan_bad_directory():
    with TestClient(app) as client:
        res = client.post("/api/scan", json={"directory": "C:\\__nonexistent__", "recursive": False})

    assert res.status_code == 400


def test_ocr_status_idle():
    with TestClient(app) as client:
        res = client.get("/api/ocr/status")

    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("idle", "running")
    assert "processed" in data
    assert "total" in data


def test_analysis_status_idle_and_cancel_safe():
    with TestClient(app) as client:
        status_res = client.get("/api/analyze/status")
        cancel_res = client.post("/api/analyze/cancel")

    assert status_res.status_code == 200
    assert cancel_res.status_code == 200
    assert status_res.json()["status"] == "idle"
    assert cancel_res.json()["running"] is False


def test_tasks_status_reports_idle_state():
    with TestClient(app) as client:
        res = client.get("/api/tasks/status")

    assert res.status_code == 200
    data = res.json()
    assert data["busy"] is False
    assert data["active_task"] is None
    assert data["ocr"]["status"] == "idle"
    assert data["analysis"]["status"] == "idle"


def test_ocr_run_rejects_when_analysis_is_running():
    with _analysis_lock:
        _analysis_state["running"] = True

    with TestClient(app) as client:
        res = client.post("/api/ocr/run", json={})

    assert res.status_code == 409
    assert res.json()["detail"] == "Analysis is already running"


def test_analysis_run_rejects_when_ocr_is_running():
    with _ocr_lock:
        _ocr_state["running"] = True

    with TestClient(app) as client:
        res = client.post("/api/analyze/run", json={"provider": "rules"})

    assert res.status_code == 409
    assert res.json()["detail"] == "OCR is already running"


def test_analysis_run_no_items_returns_idle_snapshot():
    with TestClient(app) as client:
        res = client.post("/api/analyze/run", json={"provider": "rules"})

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "idle"
    assert data["total"] == 0
    assert data["processed"] == 0


def test_stats_summarizes_library_state():
    now = utc_now()
    with connect() as conn:
        conn.executemany(
            """
            INSERT INTO items (
                source_path, filename, file_hash, file_size, ocr_status,
                analysis_source, keep_suggestion, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("C:\\img\\keep.png", "keep.png", "hash-1", 100, "done", "ai", "keep", "kept", now, now),
                ("C:\\img\\review.png", "review.png", "hash-2", 200, "pending", None, "review", "review", now, now),
                ("C:\\img\\delete.png", "delete.png", "hash-3", 300, "failed", "rules", "delete", "unreviewed", now, now),
            ],
        )

    with TestClient(app) as client:
        res = client.get("/api/stats")

    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3
    assert data["storage_bytes"] == 600
    assert data["done_ocr"] == 1
    assert data["pending_ocr"] == 1
    assert data["failed_ocr"] == 1
    assert data["analyzed"] == 2
    assert data["review_queue"] == 1
    assert data["keep_suggestion_keep"] == 1
    assert data["keep_suggestion_review"] == 1
    assert data["keep_suggestion_delete"] == 1
    assert {"name": "review", "count": 1} in data["by_status"]
    assert {"name": "ai", "count": 1} in data["by_analysis_source"]


def test_analysis_run_starts_background_batch_with_rules_provider():
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO items (
                source_path, filename, file_hash, file_size, ocr_text, ocr_status,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("C:\\img\\analysis.png", "analysis.png", "hash-analysis", 100, "Python API notes", "done", now, now),
        )

    with TestClient(app) as client:
        res = client.post("/api/analyze/run", json={"provider": "rules"})
        status_res = client.get("/api/analyze/status")

    assert res.status_code == 200
    assert status_res.status_code == 200
    data = res.json()
    assert data["status"] in {"started", "running", "idle"}
    assert data["total"] == 1
    assert "ai_used" in data
    assert "ollama_used" in data


def test_export_json():
    with TestClient(app) as client:
        res = client.get("/api/export?format=json")

    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/json")
    data = json.loads(res.text)
    assert isinstance(data, list)


def test_export_csv():
    with TestClient(app) as client:
        res = client.get("/api/export?format=csv")

    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]


def test_export_markdown():
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO items (
                source_path, filename, file_hash, file_size, ocr_text, ocr_status,
                analysis_source, category, summary, value_score, keep_suggestion,
                staleness_risk, distortion_risk, tags, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "C:\\img\\markdown.png",
                "markdown.png",
                "hash-markdown",
                100,
                "OCR text with `code`",
                "done",
                "rules",
                "Docs",
                "Useful note",
                8,
                "keep",
                "low",
                "low",
                json.dumps(["Obsidian", "export"]),
                "Review later",
                now,
                now,
            ),
        )

    with TestClient(app) as client:
        res = client.get("/api/export?format=markdown")

    assert res.status_code == 200
    assert "text/markdown" in res.headers["content-type"]
    assert res.headers["content-disposition"] == "attachment; filename=pic-text-pull.md"
    assert "# ScreenTextOrganizer Export" in res.text
    assert "## markdown.png" in res.text
    assert "| Suggestion | keep |" in res.text
    assert "| Tags | Obsidian, export |" in res.text
    assert "```text\nOCR text with `code`\n```" in res.text


def test_update_nonexistent_item():
    with TestClient(app) as client:
        res = client.patch("/api/items/99999", json={"status": "kept"})

    assert res.status_code == 404


def test_update_ocr_text_clears_stale_analysis():
    now = utc_now()
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO items (
                source_path, filename, file_hash, file_size, ocr_text, ocr_status,
                analysis_source, category, summary, value_score, keep_suggestion,
                staleness_risk, distortion_risk, tags, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "C:\\img\\analyzed.png",
                "analyzed.png",
                "hash-analyzed",
                100,
                "old text",
                "done",
                "ai",
                "old reason",
                "old summary",
                5,
                "keep",
                "old topic",
                "high",
                json.dumps(["old"]),
                now,
                now,
            ),
        )
        item_id = cur.lastrowid

    with TestClient(app) as client:
        res = client.patch(f"/api/items/{item_id}", json={"ocr_text": "new text"})

    assert res.status_code == 200
    data = res.json()
    assert data["ocr_text"] == "new text"
    assert data["analysis_source"] is None
    assert data["summary"] is None
    assert data["keep_suggestion"] is None
    assert data["tags"] == ["old"]


def test_list_items_rejects_invalid_status_filter():
    with TestClient(app) as client:
        res = client.get("/api/items?status=invalid")

    assert res.status_code == 422


def test_startup_recovers_interrupted_ocr_rows():
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO items (
                source_path, filename, file_hash, file_size, ocr_status,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("C:\\img\\running.png", "running.png", "hash-running", 100, "running", now, now),
        )

    with TestClient(app) as client:
        res = client.get("/api/items")

    assert res.status_code == 200
    item = res.json()["items"][0]
    assert item["ocr_status"] == "pending"
