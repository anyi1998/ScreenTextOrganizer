from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        res = client.get("/api/health")

    assert res.status_code == 200
    assert res.json()["ok"] is True


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


def test_update_nonexistent_item():
    with TestClient(app) as client:
        res = client.patch("/api/items/99999", json={"status": "kept"})

    assert res.status_code == 404
