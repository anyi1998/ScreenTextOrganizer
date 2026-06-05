"""Generic OpenAI-compatible AI provider client.

Works with DeepSeek, OpenAI, Kimi, Zhipu, Qwen, SiliconFlow, and any
other service that implements the OpenAI chat completions API.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from ..config import AI_API_KEY, AI_BASE_URL, AI_MODEL
from .analyzer import ANALYSIS_PROMPT, AnalysisResult, parse_analysis_json


def _get_config() -> tuple[str, str, str]:
    """Read live config values (they may be updated at runtime)."""
    from ..config import AI_API_KEY as key, AI_BASE_URL as url, AI_MODEL as model
    return key, url, model


def is_configured() -> bool:
    key, _, _ = _get_config()
    return bool(key and key != "sk-your-api-key-here")


def analyze_with_ai(
    text: str,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    timeout: int = 60,
) -> AnalysisResult | None:
    """Call an OpenAI-compatible API for content analysis."""
    env_key, env_url, env_model = _get_config()
    key = api_key or env_key
    url = base_url or env_url
    mod = model or env_model

    if not key or key == "sk-your-api-key-here":
        return None

    url = f"{url.rstrip('/')}/chat/completions"

    payload = {
        "model": mod,
        "messages": [
            {
                "role": "system",
                "content": "你是一个截图内容分析助手。只输出 JSON，不要输出其他内容。",
            },
            {
                "role": "user",
                "content": f"{ANALYSIS_PROMPT}\n\nOCR 文本：\n{text or '(空)'}",
            },
        ],
        "temperature": 0.3,
        "max_tokens": 512,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
            content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
            result = parse_analysis_json(content)
            if result:
                result.analysis_source = "ai"
            return result
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError, KeyError):
        return None


def check_connection(api_key: str | None = None, base_url: str | None = None, model: str | None = None) -> dict:
    """Check if the AI provider is reachable and return info."""
    env_key, env_url, env_model = _get_config()
    key = api_key or env_key
    url = base_url or env_url
    mod = model or env_model

    if not key or key == "sk-your-api-key-here":
        return {"available": False, "reason": "no_api_key", "model": mod, "base_url": url}

    req_url = f"{url.rstrip('/')}/models"
    headers = {
        "Authorization": f"Bearer {key}",
    }
    req = urllib.request.Request(req_url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            body = json.loads(response.read().decode("utf-8"))
            models = [m.get("id", "") for m in body.get("data", [])]
            return {
                "available": True,
                "model": mod,
                "base_url": url,
                "models_found": len(models),
            }
    except Exception:
        return {"available": False, "reason": "connection_failed", "model": mod, "base_url": url}
