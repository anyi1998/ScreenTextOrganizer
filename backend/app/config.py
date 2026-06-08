import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def _resolve_runtime_path(value: str | os.PathLike[str] | None, default: Path) -> Path:
    path = Path(value).expanduser() if value else default
    if not path.is_absolute():
        path = ROOT_DIR / path
    return path.resolve()


def _csv_env(name: str, default: str) -> tuple[str, ...]:
    raw = os.environ.get(name, default)
    return tuple(item.strip() for item in raw.split(",") if item.strip())


ENV_PATH = _resolve_runtime_path(os.environ.get("PIC_TEXT_PULL_ENV_PATH"), ROOT_DIR / ".env")


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


load_dotenv()

APP_ENV = os.environ.get("PIC_TEXT_PULL_ENV", "development").lower()
CORS_ORIGINS = _csv_env(
    "PIC_TEXT_PULL_CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
SECURITY_HEADERS_ENABLED = os.environ.get("PIC_TEXT_PULL_SECURITY_HEADERS", "1").lower() not in {
    "0",
    "false",
    "no",
}

DATA_DIR = _resolve_runtime_path(os.environ.get("PIC_TEXT_PULL_DATA_DIR"), ROOT_DIR / "data")
THUMBNAIL_DIR = DATA_DIR / "thumbnails"
DB_PATH = DATA_DIR / "pic_text_pull.db"
PADDLEX_CACHE_DIR = DATA_DIR / "paddlex-cache"
PADDLE_HOME_DIR = DATA_DIR / "paddle-home"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

# Ollama (local)
DEFAULT_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3.5:2b-q4_K_M")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

# AI Provider (OpenAI-compatible, online)
AI_API_KEY = os.environ.get("AI_API_KEY", "")
AI_BASE_URL = os.environ.get("AI_BASE_URL", "https://api.deepseek.com")
AI_MODEL = os.environ.get("AI_MODEL", "deepseek-chat")


def reload_ai_config() -> None:
    """Reload AI config from environment after .env changes."""
    global AI_API_KEY, AI_BASE_URL, AI_MODEL, DEFAULT_OLLAMA_MODEL, OLLAMA_BASE_URL
    AI_API_KEY = os.environ.get("AI_API_KEY", "")
    AI_BASE_URL = os.environ.get("AI_BASE_URL", "https://api.deepseek.com")
    AI_MODEL = os.environ.get("AI_MODEL", "deepseek-chat")
    DEFAULT_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3.5:2b-q4_K_M")
    OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")


def save_ai_config(api_key: str, base_url: str, model: str, clear_api_key: bool = False) -> None:
    """Write AI config to .env file and update runtime config."""
    lines: list[str] = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()

    current_key = os.environ.get("AI_API_KEY", "")
    next_key = "" if clear_api_key else (api_key or current_key)
    env_map = {"AI_API_KEY": next_key, "AI_BASE_URL": base_url, "AI_MODEL": model}
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
