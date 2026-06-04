from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import httpx
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "data" / "sample-images"
DB_PATH = ROOT / "data" / "pic_text_pull.db"
API = "http://127.0.0.1:8000"


def make_sample() -> Path:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    image_path = SAMPLE_DIR / "rapidocr-smoke.png"
    img = Image.new("RGB", (1000, 420), "white")
    draw = ImageDraw.Draw(img)
    draw.text((48, 72), "React Hook interview question useEffect cache", fill=(20, 30, 40))
    img.save(image_path)
    return image_path


def reset_sample() -> None:
    if not DB_PATH.exists():
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            UPDATE items
            SET ocr_status = 'done'
            WHERE filename != 'rapidocr-smoke.png'
            """
        )
        conn.execute(
            """
            UPDATE items
            SET ocr_text = '', ocr_status = 'pending', ocr_error = NULL
            WHERE filename = 'rapidocr-smoke.png'
            """
        )
        conn.commit()
    finally:
        conn.close()


def main() -> None:
    image_path = make_sample()
    with httpx.Client(timeout=240) as client:
        health = client.get(f"{API}/api/health").json()
        scan = client.post(
            f"{API}/api/scan",
            json={"directory": str(image_path.parent), "recursive": True},
        ).json()
        reset_sample()
        ocr = client.post(f"{API}/api/ocr/run", json={"limit": 1}).json()
        analyze = client.post(
            f"{API}/api/analyze/run",
            json={"use_ollama": False, "include_image": False, "limit": 10},
        ).json()
        time.sleep(0.5)
        items = client.get(f"{API}/api/items", params={"q": "rapidocr-smoke"}).json()["items"]
    print({"health": health, "scan": scan, "ocr": ocr, "analyze": analyze, "item": items[0] if items else None})


if __name__ == "__main__":
    main()
