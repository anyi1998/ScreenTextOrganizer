from app.services.analyzer import analyze_text_rules, parse_analysis_json


def test_rules_analysis_tags_interview_like_content():
    result = analyze_text_rules("React componentWillMount 生命周期面试题，Webpack 4 如何配置 loader")

    assert result.analysis_source == "rules"
    assert result.keep_suggestion == "review"
    assert result.distortion_risk == "high"
    assert result.value_score == 3
    assert "职场" in result.tags


def test_low_quality_text_is_suggested_for_deletion():
    result = analyze_text_rules("@@@@@@@")

    assert result.distortion_risk == "low"
    assert result.keep_suggestion == "delete"


def test_parse_analysis_json_maps_ai_schema_to_storage_fields():
    result = parse_analysis_json(
        """
        extra text
        {
          "summary": "A useful note",
          "topic": "engineering",
          "value_score": 4,
          "keep_suggestion": "keep",
          "keep_reason": "high signal",
          "ocr_quality": "high",
          "tags": ["code", "react", "ui", "notes", "extra", "ignored"]
        }
        """
    )

    assert result is not None
    assert result.analysis_source == "ai"
    assert result.category == "high signal"
    assert result.staleness_risk == "engineering"
    assert result.distortion_risk == "high"
    assert result.tags == ["code", "react", "ui", "notes", "extra"]
