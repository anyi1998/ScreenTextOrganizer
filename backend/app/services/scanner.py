from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from ..config import IMAGE_EXTENSIONS
from ..database import connect, json_tags, normalize_path, utc_now
from .thumbnails import generate_thumbnail


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iso_from_timestamp(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def iter_images(directory: Path, recursive: bool) -> list[Path]:
    pattern = "**/*" if recursive else "*"
    return [
        path
        for path in directory.glob(pattern)
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]


def scan_directory(directory: str, recursive: bool = True) -> dict[str, object]:
    root = Path(directory).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Directory does not exist: {root}")

    scanned = 0
    inserted = 0
    updated = 0
    unchanged = 0
    failed = 0
    errors: list[dict[str, str]] = []

    with connect() as conn:
        for image_path in iter_images(root, recursive):
            scanned += 1
            try:
                stat = image_path.stat()
                file_hash = sha256_file(image_path)
                now = utc_now()
                source_path = normalize_path(image_path)

                existing = conn.execute(
                    "SELECT id, file_hash FROM items WHERE source_path = ?", (source_path,)
                ).fetchone()
                if existing:
                    if existing["file_hash"] == file_hash:
                        unchanged += 1
                        continue

                    thumbnail_path, width, height = generate_thumbnail(image_path, file_hash)
                    conn.execute(
                        """
                        UPDATE items
                        SET file_hash = ?, file_size = ?, width = ?, height = ?,
                            modified_time = ?, thumbnail_path = ?,
                            ocr_text = '', ocr_confidence = NULL, ocr_status = 'pending',
                            ocr_error = NULL, analysis_source = NULL, category = NULL,
                            summary = NULL, value_score = NULL, keep_suggestion = NULL,
                            staleness_risk = NULL, distortion_risk = NULL, tags = ?,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            file_hash,
                            stat.st_size,
                            width,
                            height,
                            iso_from_timestamp(stat.st_mtime),
                            thumbnail_path,
                            json_tags([]),
                            now,
                            existing["id"],
                        ),
                    )
                    updated += 1
                else:
                    thumbnail_path, width, height = generate_thumbnail(image_path, file_hash)
                    conn.execute(
                        """
                        INSERT INTO items (
                            source_path, filename, file_hash, file_size, width, height,
                            created_time, modified_time, thumbnail_path, tags,
                            created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            source_path,
                            image_path.name,
                            file_hash,
                            stat.st_size,
                            width,
                            height,
                            iso_from_timestamp(stat.st_ctime),
                            iso_from_timestamp(stat.st_mtime),
                            thumbnail_path,
                            json_tags([]),
                            now,
                            now,
                        ),
                    )
                    inserted += 1
            except Exception as exc:
                failed += 1
                errors.append({"file": str(image_path), "error": str(exc)})

    return {
        "scanned": scanned,
        "inserted": inserted,
        "updated": updated,
        "unchanged": unchanged,
        "failed": failed,
        "errors": errors,
    }
