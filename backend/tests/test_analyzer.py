from app.services.analyzer import analyze_text_rules


def test_frontend_interview_stale_detection():
    result = analyze_text_rules("React componentWillMount 生命周期面试题，Webpack 4 如何配置 loader")

    assert result.category == "frontend_interview"
    assert result.staleness_risk == "high"
    assert result.keep_suggestion in {"review", "keep", "delete"}
    assert "Possibly outdated" in result.tags


def test_low_quality_text_distortion():
    result = analyze_text_rules("@@@@@@@")

    assert result.distortion_risk == "high"
    assert result.keep_suggestion == "delete"

