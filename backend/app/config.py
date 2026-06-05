import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
THUMBNAIL_DIR = DATA_DIR / "thumbnails"
DB_PATH = DATA_DIR / "pic_text_pull.db"
PADDLEX_CACHE_DIR = DATA_DIR / "paddlex-cache"
PADDLE_HOME_DIR = DATA_DIR / "paddle-home"
ENV_PATH = ROOT_DIR / ".env"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

# Ollama (local)
DEFAULT_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3.5:2b-q4_K_M")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

# AI Provider (OpenAI-compatible, online)
AI_API_KEY = os.environ.get("AI_API_KEY", "")
AI_BASE_URL = os.environ.get("AI_BASE_URL", "https://api.deepseek.com")
AI_MODEL = os.environ.get("AI_MODEL", "deepseek-chat")


def ensure_runtime_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
    PADDLEX_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    PADDLE_HOME_DIR.mkdir(parents=True, exist_ok=True)


def load_dotenv() -> None:
    """Load .env file into os.environ if it exists."""
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        os.environ.setdefault(key, value)


def reload_ai_config() -> None:
    """Reload AI config from environment after .env changes."""
    global AI_API_KEY, AI_BASE_URL, AI_MODEL, DEFAULT_OLLAMA_MODEL, OLLAMA_BASE_URL
    AI_API_KEY = os.environ.get("AI_API_KEY", "")
    AI_BASE_URL = os.environ.get("AI_BASE_URL", "https://api.deepseek.com")
    AI_MODEL = os.environ.get("AI_MODEL", "deepseek-chat")
    DEFAULT_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3.5:2b-q4_K_M")
    OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")


def save_ai_config(api_key: str, base_url: str, model: str) -> None:
    """Write AI config to .env file and update runtime config."""
    lines: list[str] = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()

    env_map = {"AI_API_KEY": api_key, "AI_BASE_URL": base_url, "AI_MODEL": model}
    updated_keys: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in env_map:
                new_lines.append(f"{key}={env_map[key]}")
                updated_keys.add(key)
                continue
        new_lines.append(line)

    for key, value in env_map.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}")

    ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    for key, value in env_map.items():
        os.environ[key] = value
    reload_ai_config()


# Auto-load .env on module import
load_dotenv()
