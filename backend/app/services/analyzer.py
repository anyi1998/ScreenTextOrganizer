from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict


@dataclass
class AnalysisResult:
    analysis_source: str
    category: str
    summary: str
    value_score: int
    keep_suggestion: str
    staleness_risk: str
    distortion_risk: str
    tags: list[str]


FRONTEND_KEYWORDS = {
    "React": ["react", "jsx", "hooks", "useeffect", "usestate", "fiber"],
    "Vue": ["vue", "vuex", "pinia", "computed", "watch"],
    "JavaScript": ["javascript", "js", "闭包", "原型链", "事件循环", "promise", "async", "await"],
    "CSS": ["css", "flex", "grid", "盒模型", "布局", "选择器"],
    "HTTP": ["http", "缓存", "cookie", "跨域", "cors", "cdn"],
    "Build": ["webpack", "vite", "babel", "loader", "plugin"],
}

STALE_PATTERNS = [
    "componentwillmount",
    "componentwillreceiveprops",
    "componentwillupdate",
    "vue2",
    "vue 2",
    "jquery",
    "ie8",
    "ie9",
    "attachEvent".lower(),
    "webpack3",
    "webpack 3",
    "webpack4",
    "webpack 4",
]


def analyze_text_rules(text: str) -> AnalysisResult:
    normalized = (text or "").strip()
    lower = normalized.lower()
    tags: list[str] = []

    for tag, keywords in FRONTEND_KEYWORDS.items():
        if any(keyword.lower() in lower or keyword in normalized for keyword in keywords):
            tags.append(tag)

    if any(term in lower for term in ["面试", "八股", "问：", "答：", "interview"]) or (
        "question" in lower and tags
    ):
        category = "frontend_interview" if tags else "interview"
    elif any(term in lower for term in ["function", "const ", "let ", "class ", "error", "exception"]):
        category = "code"
    elif any(term in normalized for term in ["读书", "书摘", "摘录", "作者", "章节", "书中", "这本书"]):
        category = "book_excerpt"
    elif any(term in normalized for term in ["灵感", "想法", "启发", "可以做", "值得"]):
        category = "idea"
    elif len(normalized) < 8:
        category = "low_text"
    else:
        category = "note"

    stale = any(pattern in lower for pattern in STALE_PATTERNS)
    staleness_risk = "high" if stale else ("medium" if category == "frontend_interview" else "low")

    distortion_risk = estimate_distortion_risk(normalized)
    value_score = estimate_value_score(normalized, category, staleness_risk, distortion_risk)
    keep_suggestion = suggest_keep(value_score, distortion_risk)
    summary = build_summary(normalized, category)

    if category == "frontend_interview" and "Frontend" not in tags:
        tags.insert(0, "Frontend")
    if stale and "Possibly outdated" not in tags:
        tags.append("Possibly outdated")

    return AnalysisResult(
        analysis_source="rules",
        category=category,
        summary=summary,
        value_score=value_score,
        keep_suggestion=keep_suggestion,
        staleness_risk=staleness_risk,
        distortion_risk=distortion_risk,
        tags=tags[:8],
    )


def estimate_distortion_risk(text: str) -> str:
    if not text:
        return "high"
    if not re.search(r"[\w\u4e00-\u9fff]", text):
        return "high"
    if len(text) < 12:
        return "medium"
    unusual = len(re.findall(r"[^\w\s\u4e00-\u9fff，。！？；：、（）《》【】“”‘’.,!?;:()\\[\\]{}<>/+-]", text))
    ratio = unusual / max(len(text), 1)
    repeated = bool(re.search(r"(.)\1{6,}", text))
    if ratio > 0.18 or repeated:
        return "high"
    if ratio > 0.08:
        return "medium"
    return "low"


def estimate_value_score(text: str, category: str, staleness_risk: str, distortion_risk: str) -> int:
    score = 3
    if category in {"book_excerpt", "idea", "frontend_interview", "code"}:
        score += 1
    if len(text) > 120:
        score += 1
    if staleness_risk == "high":
        score -= 1
    if distortion_risk == "high":
        score -= 2
    if distortion_risk == "medium":
        score -= 1
    return min(5, max(1, score))


def suggest_keep(value_score: int, distortion_risk: str) -> str:
    if distortion_risk == "high" or value_score <= 2:
        return "delete"
    if value_score >= 4:
        return "keep"
    return "review"


def build_summary(text: str, category: str) -> str:
    if not text:
        return "未识别出有效文字。"
    compact = re.sub(r"\s+", " ", text)
    prefix = {
        "frontend_interview": "前端面试题或相关知识点",
        "book_excerpt": "书摘或阅读记录",
        "idea": "灵感或想法记录",
        "code": "代码或技术截图",
        "low_text": "文字信息较少",
    }.get(category, "普通笔记")
    return f"{prefix}：{compact[:90]}{'...' if len(compact) > 90 else ''}"


def parse_analysis_json(raw: str) -> AnalysisResult | None:
    try:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1:
            return None
        data = json.loads(raw[start : end + 1])
        return AnalysisResult(
            analysis_source="ollama",
            category=str(data.get("category") or "note"),
            summary=str(data.get("summary") or ""),
            value_score=int(data.get("value_score") or 3),
            keep_suggestion=str(data.get("keep_suggestion") or "review"),
            staleness_risk=str(data.get("staleness_risk") or "low"),
            distortion_risk=str(data.get("distortion_risk") or "low"),
            tags=[str(tag) for tag in data.get("tags", [])][:8],
        )
    except Exception:
        return None


def to_update_dict(result: AnalysisResult) -> dict:
    data = asdict(result)
    data["tags"] = json.dumps(result.tags, ensure_ascii=False)
    return data


def merge_ollama_with_rules(ollama: AnalysisResult, rules: AnalysisResult) -> AnalysisResult:
    generic_categories = {"other", "note", "low_text", ""}
    if ollama.category in generic_categories and rules.category not in generic_categories:
        ollama.category = rules.category
    if rules.staleness_risk == "high" and ollama.staleness_risk != "high":
        ollama.staleness_risk = "high"
    if rules.distortion_risk == "high" and ollama.distortion_risk != "high":
        ollama.distortion_risk = "high"
    merged_tags = list(dict.fromkeys([*rules.tags, *ollama.tags]))
    ollama.tags = merged_tags[:8]
    return ollama
