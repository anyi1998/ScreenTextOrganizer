from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .config import DB_PATH, ensure_runtime_dirs


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    ensure_runtime_dirs()
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_path TEXT NOT NULL UNIQUE,
                filename TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                width INTEGER,
                height INTEGER,
                created_time TEXT,
                modified_time TEXT,
                thumbnail_path TEXT,
                ocr_text TEXT DEFAULT '',
                ocr_confidence REAL,
                ocr_status TEXT NOT NULL DEFAULT 'pending',
                ocr_error TEXT,
                analysis_source TEXT,
                category TEXT,
                summary TEXT,
                value_score INTEGER,
                keep_suggestion TEXT,
                staleness_risk TEXT,
                distortion_risk TEXT,
                tags TEXT DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'unreviewed',
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                trashed_at TEXT,
                trash_error TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_items_status ON items(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_items_ocr_status ON items(ocr_status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_items_category ON items(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_items_keep_suggestion ON items(keep_suggestion)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_items_updated_at ON items(updated_at)")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    ensure_runtime_dirs()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    tags = data.get("tags")
    if isinstance(tags, str):
        try:
            data["tags"] = json.loads(tags)
        except json.JSONDecodeError:
            data["tags"] = []
    return data


def json_tags(tags: list[str] | None) -> str:
    return json.dumps(tags or [], ensure_ascii=False)


def normalize_path(path: str | Path) -> str:
    return str(Path(path).expanduser().resolve())
