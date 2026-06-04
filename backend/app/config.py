import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
THUMBNAIL_DIR = DATA_DIR / "thumbnails"
DB_PATH = DATA_DIR / "pic_text_pull.db"
PADDLEX_CACHE_DIR = DATA_DIR / "paddlex-cache"
PADDLE_HOME_DIR = DATA_DIR / "paddle-home"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
DEFAULT_OLLAMA_MODEL = "qwen3.5:2b-q4_K_M"
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")


def ensure_runtime_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
    PADDLEX_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    PADDLE_HOME_DIR.mkdir(parents=True, exist_ok=True)
