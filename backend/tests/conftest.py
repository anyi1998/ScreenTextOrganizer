from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


_RUNTIME_DIR = tempfile.TemporaryDirectory()
_RUNTIME_PATH = Path(_RUNTIME_DIR.name)

os.environ["PIC_TEXT_PULL_DATA_DIR"] = str(_RUNTIME_PATH / "data")
os.environ["PIC_TEXT_PULL_ENV_PATH"] = str(_RUNTIME_PATH / ".env")
os.environ["AI_API_KEY"] = ""


@pytest.fixture(autouse=True)
def reset_database():
    from app import config
    from app.database import connect, init_db
    from app.main import _analysis_lock, _analysis_state, _ocr_lock, _ocr_state

    config.ENV_PATH.unlink(missing_ok=True)
    os.environ["AI_API_KEY"] = ""
    os.environ["AI_BASE_URL"] = "https://api.deepseek.com"
    os.environ["AI_MODEL"] = "deepseek-chat"
    config.reload_ai_config()
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
                "finished_at": None,
                "last_error": None,
            }
        )
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
                "finished_at": None,
                "last_error": None,
            }
        )

    init_db()
    with connect() as conn:
        conn.execute("DELETE FROM items")
    yield
    with connect() as conn:
        conn.execute("DELETE FROM items")
    config.ENV_PATH.unlink(missing_ok=True)
