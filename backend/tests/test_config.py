from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app import config
from app.main import app
from app.services import ai_provider


def test_save_ai_config_preserves_existing_key_when_key_is_omitted():
    config.save_ai_config("first-key", "https://api.example.com", "model-a")
    config.save_ai_config("", "https://api.changed.example.com", "model-b")

    assert config.AI_API_KEY == "first-key"
    assert config.AI_BASE_URL == "https://api.changed.example.com"
    assert config.AI_MODEL == "model-b"
    assert "AI_API_KEY=first-key" in config.ENV_PATH.read_text(encoding="utf-8")


def test_save_ai_config_can_clear_existing_key():
    config.save_ai_config("first-key", "https://api.example.com", "model-a")
    config.save_ai_config("", "https://api.example.com", "model-a", clear_api_key=True)

    assert config.AI_API_KEY == ""
    assert "AI_API_KEY=" in config.ENV_PATH.read_text(encoding="utf-8")


def test_ai_config_api_masks_key_and_preserves_it_when_omitted(monkeypatch):
    monkeypatch.setattr("app.main.check_connection", lambda *args, **kwargs: {"available": True})

    with TestClient(app) as client:
        res = client.post(
            "/api/config/ai",
            json={"api_key": "sk-test-secret", "base_url": "https://api.example.com", "model": "model-a"},
        )
        assert res.status_code == 200

        res = client.post(
            "/api/config/ai",
            json={"api_key": "", "base_url": "https://api.changed.example.com", "model": "model-b"},
        )
        assert res.status_code == 200

        config_res = client.get("/api/config/ai")

    assert config_res.status_code == 200
    data = config_res.json()
    assert data["api_key_set"] is True
    assert data["api_key_masked"].startswith("sk-t")
    assert data["base_url"] == "https://api.changed.example.com"
    assert data["model"] == "model-b"
    assert config.AI_API_KEY == "sk-test-secret"


def test_ocr_cancel_is_safe_when_idle():
    with TestClient(app) as client:
        res = client.post("/api/ocr/cancel")

    assert res.status_code == 200
    data = res.json()
    assert data["running"] is False
    assert data["status"] == "idle"


def test_ai_provider_uses_resolved_env_api_key(monkeypatch):
    config.save_ai_config("env-secret", "https://api.example.com", "model-a")
    captured: dict[str, str | None] = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self) -> bytes:
            content = json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "summary": "summary",
                                        "topic": "topic",
                                        "value_score": 3,
                                        "keep_suggestion": "review",
                                        "keep_reason": "reason",
                                        "ocr_quality": "high",
                                        "tags": ["tag"],
                                    }
                                )
                            }
                        }
                    ]
                }
            )
            return content.encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["authorization"] = request.get_header("Authorization")
        captured["url"] = request.full_url
        return FakeResponse()

    monkeypatch.setattr(ai_provider.urllib.request, "urlopen", fake_urlopen)

    result = ai_provider.analyze_with_ai("hello")

    assert result is not None
    assert result.analysis_source == "ai"
    assert captured["authorization"] == "Bearer env-secret"
    assert captured["url"] == "https://api.example.com/chat/completions"
