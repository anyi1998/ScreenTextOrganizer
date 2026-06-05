from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict


@dataclass
class AnalysisResult:
    analysis_source: str
    category: str       # reused for keep_reason
    summary: str
    value_score: int
    keep_suggestion: str
    staleness_risk: str  # reused for topic
    distortion_risk: str  # reused for ocr_quality
    tags: list[str]


# ── Shared AI prompt (used by ai_provider and ollama) ──────────────────

ANALYSIS_PROMPT = """\
你是一个截图整理助手。用户会截图保存各种有用的信息（知乎讨论、读书笔记、新闻、教程、聊天记录、代码等等）。
请根据 OCR 文字分析这张截图的内容。

输出 JSON，字段如下：
{
  "summary": "一句话概括截图的核心内容。要求提炼要点，不要复述原文。",
  "topic": "内容的话题或主题，如：房产投资、编程技术、读书感悟、职场经验、生活技巧、健康养生等",
  "value_score": "1-5 的整数。5=非常有价值的知识或观点，1=碎片信息、无实质内容",
  "keep_suggestion": "keep（值得保留）/ review（需要人工判断）/ delete（建议删除）",
  "keep_reason": "简短说明保留或删除的理由",
  "time_sensitive": false,
  "ocr_quality": "low/medium/high — OCR 文字是否完整可读，有无乱码或大量缺失",
  "tags": ["标签1", "标签2"]
}

评判标准：
- 有具体知识点、数据、独到观点、实用方法的 → 高分（4-5）
- 有一定信息但不够深入或太碎片化的 → 中分（3）
- 纯闲聊、无实质信息、重复内容、纯 UI 界面截图 → 低分（1-2）
- 内容涉及价格、政策、排名、市场数据等随时间变化的信息 → time_sensitive 设为 true
- OCR 文字有明显乱码、大量不可读字符、或文字极少 → ocr_quality 设为 low
- tags 最多 5 个，用中文，反映内容主题""".strip()


# ── Rules-based fallback analysis ──────────────────────────────────────

def analyze_text_rules(text: str) -> AnalysisResult:
    """Lightweight rules-based analysis as fallback when no AI is available."""
    normalized = (text or "").strip()
    lower = normalized.lower()
    tags: list[str] = []

    # ── Basic content detection for tags ──
    tag_patterns: dict[str, list[str]] = {
        "技术": ["代码", "代碼", "function", "const ", "class ", "def ", "import ", "error", "bug", "api"],
        "读书": ["读书", "书摘", "摘录", "这本书", "作者说", "章节", "读后感"],
        "投资": ["投资", "理财", "基金", "股票", "房价", "房产", "收益率"],
        "职场": ["面试", "简历", "工资", "涨薪", "跳槽", "offer"],
        "生活": ["食谱", "健身", "减肥", "旅游", "攻略"],
    }
    for tag, keywords in tag_patterns.items():
        if any(k in lower or k in normalized for k in keywords):
            tags.append(tag)

    # ── OCR quality estimation ──
    ocr_quality = _estimate_ocr_quality(normalized)

    # ── Value score ──
    score = 3
    if len(normalized) > 150:
        score += 1
    if len(normalized) > 400:
        score += 1
    if len(normalized) < 15:
        score -= 2
    if ocr_quality == "low":
        score -= 2
    elif ocr_quality == "medium":
        score -= 1
    score = min(5, max(1, score))

    # ── Keep suggestion ──
    if ocr_quality == "low" or score <= 1:
        keep_suggestion = "delete"
    elif score >= 4:
        keep_suggestion = "keep"
    else:
        keep_suggestion = "review"

    # ── Summary (basic: truncate, and note AI is recommended) ──
    if not normalized:
        summary = "未识别出有效文字。"
    else:
        compact = re.sub(r"\s+", " ", normalized)
        preview = compact[:80] + ("..." if len(compact) > 80 else "")
        summary = preview

    # ── Topic guess ──
    topic = tags[0] if tags else "未分类"

    # ── Keep reason ──
    if score >= 4:
        keep_reason = "内容较丰富，建议保留"
    elif ocr_quality == "low":
        keep_reason = "OCR 质量较差，文字可能不完整"
    elif len(normalized) < 15:
        keep_reason = "文字信息过少"
    else:
        keep_reason = "建议启用 AI 分析以获得更准确的判断"

    return AnalysisResult(
        analysis_source="rules",
        category=keep_reason,
        summary=summary,
        value_score=score,
        keep_suggestion=keep_suggestion,
        staleness_risk=topic,
        distortion_risk=ocr_quality,
        tags=tags[:5],
    )


def _estimate_ocr_quality(text: str) -> str:
    """Estimate OCR quality based on character patterns."""
    if not text:
        return "low"
    if not re.search(r"[\w\u4e00-\u9fff]", text):
        return "low"
    if len(text) < 10:
        return "medium"
    unusual = len(re.findall(r"[^\w\s\u4e00-\u9fff，。！？；：、（）《》【】""''.,!?;:()\\{}<>/+@#$%&*=~`|-]", text))
    ratio = unusual / max(len(text), 1)
    repeated = bool(re.search(r"(.)\1{6,}", text))
    if ratio > 0.15 or repeated:
        return "low"
    if ratio > 0.06:
        return "medium"
    return "high"


# ── JSON parsing ──────────────────────────────────────────────────────

def parse_analysis_json(raw: str) -> AnalysisResult | None:
    """Parse AI response JSON into AnalysisResult, mapping new fields to DB columns."""
    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1:
            return None
        data = json.loads(raw[start : end + 1])
        return AnalysisResult(
            analysis_source="ai",
            category=str(data.get("keep_reason") or ""),
            summary=str(data.get("summary") or ""),
            value_score=int(data.get("value_score") or 3),
            keep_suggestion=str(data.get("keep_suggestion") or "review"),
            staleness_risk=str(data.get("topic") or ""),
            distortion_risk=str(data.get("ocr_quality") or "medium"),
            tags=[str(tag) for tag in data.get("tags", [])][:5],
        )
    except Exception:
        return None


def to_update_dict(result: AnalysisResult) -> dict:
    data = asdict(result)
    data["tags"] = json.dumps(result.tags, ensure_ascii=False)
    return data


def merge_ai_with_rules(ai_result: AnalysisResult, rules_result: AnalysisResult) -> AnalysisResult:
    """Merge AI analysis with rules-based checks (e.g., OCR quality override)."""
    # If rules detect bad OCR quality but AI didn't, trust rules
    if rules_result.distortion_risk == "low" and ai_result.distortion_risk != "low":
        ai_result.distortion_risk = rules_result.distortion_risk
    # Merge tags (AI tags first, then rules tags for anything extra)
    merged_tags = list(dict.fromkeys([*ai_result.tags, *rules_result.tags]))
    ai_result.tags = merged_tags[:5]
    return ai_result
