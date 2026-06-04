from __future__ import annotations

from pathlib import Path

from PIL import Image

from ..config import THUMBNAIL_DIR


def generate_thumbnail(source: Path, file_hash: str) -> tuple[str, int | None, int | None]:
    thumb_path = THUMBNAIL_DIR / f"{file_hash}.jpg"
    width: int | None = None
    height: int | None = None

    with Image.open(source) as img:
        width, height = img.size
        img.thumbnail((360, 360))
        rgb = img.convert("RGB")
        rgb.save(thumb_path, "JPEG", quality=86)

    return str(thumb_path), width, height

