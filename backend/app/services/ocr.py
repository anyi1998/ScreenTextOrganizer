from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
from typing import Any

from ..config import PADDLE_HOME_DIR, PADDLEX_CACHE_DIR, ensure_runtime_dirs
from .ollama import ocr_with_ollama


_paddle_disabled_error: str | None = None
_rapid_disabled_error: str | None = None


@lru_cache(maxsize=1)
def get_rapid_ocr() -> Any:
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


@lru_cache(maxsize=1)
def get_paddle_ocr() -> Any:
    ensure_runtime_dirs()
    os.environ["PADDLE_PDX_CACHE_HOME"] = str(PADDLEX_CACHE_DIR)
    os.environ["HOME"] = str(PADDLE_HOME_DIR)
    os.environ["USERPROFILE"] = str(PADDLE_HOME_DIR)
    from paddleocr import PaddleOCR

    return PaddleOCR(
        lang="ch",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )


def run_ocr(image_path: str) -> tuple[str, float | None]:
    global _paddle_disabled_error, _rapid_disabled_error
    path = str(Path(image_path))
    if _paddle_disabled_error is not None:
        rapid = run_rapid_ocr(path)
        if rapid[0]:
            return rapid
        fallback = ocr_with_ollama(path)
        if fallback:
            return fallback, None
        raise RuntimeError(
            "PaddleOCR unavailable, RapidOCR unavailable, and Ollama OCR fallback failed: "
            f"{_paddle_disabled_error}; {_rapid_disabled_error}"
        )

    try:
        ocr = get_paddle_ocr()
        result = ocr.ocr(path)
    except Exception as exc:
        _paddle_disabled_error = str(exc)
        rapid = run_rapid_ocr(path)
        if rapid[0]:
            return rapid
        fallback = ocr_with_ollama(path)
        if fallback:
            return fallback, None
        raise RuntimeError(f"PaddleOCR unavailable and OCR fallbacks failed: {exc}; {_rapid_disabled_error}") from exc

    lines: list[str] = []
    scores: list[float] = []

    def consume(node: Any) -> None:
        if isinstance(node, tuple) and len(node) == 2 and isinstance(node[0], str):
            lines.append(node[0])
            if isinstance(node[1], (int, float)):
                scores.append(float(node[1]))
        elif isinstance(node, list):
            if len(node) >= 2 and isinstance(node[1], tuple):
                consume(node[1])
            else:
                for child in node:
                    consume(child)

    consume(result)
    confidence = sum(scores) / len(scores) if scores else None
    text = "\n".join(line for line in lines if line).strip()
    if text:
        return text, confidence
    rapid = run_rapid_ocr(path)
    if rapid[0]:
        return rapid
    fallback = ocr_with_ollama(path)
    if fallback:
        return fallback, None
    return "", confidence


def run_rapid_ocr(image_path: str) -> tuple[str, float | None]:
    global _rapid_disabled_error
    if _rapid_disabled_error is not None:
        return "", None
    try:
        engine = get_rapid_ocr()
        result, _ = engine(image_path)
        if not result:
            return "", None
        lines: list[str] = []
        scores: list[float] = []
        for item in result:
            if len(item) >= 2:
                lines.append(str(item[1]))
            if len(item) >= 3 and isinstance(item[2], (int, float)):
                scores.append(float(item[2]))
        confidence = sum(scores) / len(scores) if scores else None
        return "\n".join(line for line in lines if line).strip(), confidence
    except Exception as exc:
        _rapid_disabled_error = str(exc)
        return "", None
