from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from pathlib import Path

from ..config import DEFAULT_OLLAMA_MODEL, OLLAMA_BASE_URL
from .analyzer import AnalysisResult, parse_analysis_json


OLLAMA_URL = f"{OLLAMA_BASE_URL}/api/chat"


def analyze_with_ollama(
    text: str,
    image_path: str | None = None,
    include_image: bool = False,
    model: str | None = None,
    timeout: int = 90,
) -> AnalysisResult | None:
    prompt = """
你是一个本地图片资料整理助手。请根据 OCR 文本和可选图片内容，判断这张截图是否值得保留。
只输出 JSON，不要输出 Markdown。
字段必须是：
category: frontend_interview/book_excerpt/idea/code/note/low_text/other
summary: 中文一句话摘要
value_score: 1 到 5 的整数
keep_suggestion: keep/delete/review
staleness_risk: low/medium/high
distortion_risk: low/medium/high
tags: 字符串数组，最多 8 个

判断重点：
- 前端面试题是否偏老，例如 React 旧生命周期、Vue2 专属写法、jQuery、IE 兼容、旧 Webpack 配置。
- OCR 文本是否疑似失真、乱码、信息不足。
- 书摘或启发是否有复用价值。

OCR 文本：
""".strip()

    message: dict = {
        "role": "user",
        "content": f"{prompt}\n{text or '(空)'}\n/no_think",
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
            return parse_analysis_json(content)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None


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
