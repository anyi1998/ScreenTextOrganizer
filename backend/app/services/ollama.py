from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from pathlib import Path

from ..config import DEFAULT_OLLAMA_MODEL, OLLAMA_BASE_URL
from .analyzer import ANALYSIS_PROMPT, AnalysisResult, parse_analysis_json


OLLAMA_URL = f"{OLLAMA_BASE_URL}/api/chat"


def analyze_with_ollama(
    text: str,
    image_path: str | None = None,
    include_image: bool = False,
    model: str | None = None,
    timeout: int = 90,
) -> AnalysisResult | None:
    prompt = ANALYSIS_PROMPT

    message: dict = {
        "role": "user",
        "content": f"{prompt}\n\nOCR 文本：\n{text or '(空)'}\n/no_think",
    }

    if include_image and image_path:
        try:
            image_bytes = Path(image_path).read_bytes()
            message["images"] = [base64.b64encode(image_bytes).decode("ascii")]
        except OSError:
            pass

    payload = {
        "model": model or DEFAULT_OLLAMA_MODEL,
        "messages": [message],
        "stream": False,
        "format": "json",
        "think": False,
        "options": {"temperature": 0.1},
    }

    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
            content = body.get("message", {}).get("content", "")
            result = parse_analysis_json(content)
            if result:
                result.analysis_source = "ollama"
            return result
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None


def check_ollama() -> dict:
    """Check if Ollama is running and return available models."""
    try:
        req = urllib.request.Request(
            f"{OLLAMA_BASE_URL}/api/tags",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            body = json.loads(response.read().decode("utf-8"))
            models = [m.get("name", "") for m in body.get("models", [])]
            return {"available": True, "models": models}
    except Exception:
        return {"available": False, "models": []}


def ocr_with_ollama(
    image_path: str,
    model: str | None = None,
    timeout: int = 120,
) -> str | None:
    try:
        image_bytes = Path(image_path).read_bytes()
    except OSError:
        return None

    payload = {
        "model": model or DEFAULT_OLLAMA_MODEL,
        "messages": [
            {
                "role": "user",
                "content": "请提取图片中的所有可见文字，只输出文字本身，不要解释。/no_think",
                "images": [base64.b64encode(image_bytes).decode("ascii")],
            }
        ],
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "num_predict": 1024},
    }

    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
            content = body.get("message", {}).get("content", "").strip()
            if not content or content.lower() in {"none", "null", "无"}:
                return None
            return content
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None
