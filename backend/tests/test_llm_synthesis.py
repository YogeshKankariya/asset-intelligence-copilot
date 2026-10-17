"""Tests for Milestone 8: Grounded LLM Answer Synthesis.

Verifies:
1. Valid synthesis from supplied evidence.
2. Missing API key uses the fallback.
3. Provider errors and timeouts use the fallback.
4. Unsupported questions remain unsupported.
5. Citations cannot reference nonexistent evidence.
6. Contradictory evidence remains disclosed.
7. Deterministic production and compliance results are not altered by the model.
8. Existing tests remain passing.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from app.assistant import AssistantAskResponse, process_assistant_question
from app.llm_synthesis import (
    GeminiProvider,
    LLMConfig,
    MockProvider,
    OpenAIProvider,
    get_llm_config,
    get_llm_provider,
    synthesize_grounded_answer,
    validate_citations,
    validate_deterministic_preservation,
)
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Missing API key or disabled configuration uses fallback
# ---------------------------------------------------------------------------


def test_missing_api_key_uses_fallback(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_ENABLED", "true")

    response = client.post(
        "/api/assistant/ask",
        json={"question": "Is WELL-0001 producing?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert "not producing" in data["answer"].lower()
    # Fallback to deterministic baseline; llm_synthesized is False or not set
    assert not data.get("details", {}).get("llm_synthesized", False)


def test_disabled_llm_config_uses_fallback(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "false")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-12345")

    cfg = get_llm_config()
    assert cfg.enabled is False

    provider = get_llm_provider(cfg)
    assert provider is None


# ---------------------------------------------------------------------------
# 2. Valid synthesis from supplied evidence
# ---------------------------------------------------------------------------


def test_valid_synthesis_from_supplied_evidence(monkeypatch):
    mock = MockProvider(
        response_text=(
            "Well WELL-0001 is classified as not producing based on the latest valid inspection "
            "INS-0001-0203. The wellhead temperature was 18.0°C and ambient was 10.0°C, a difference of 8.0°C, "
            "which is below the required 15.0°C threshold for T200 wells."
        )
    )

    # Monkeypatch get_llm_provider to return our mock provider
    monkeypatch.setattr("app.llm_synthesis.get_llm_provider", lambda cfg=None: mock)

    response = client.post(
        "/api/assistant/ask",
        json={"question": "Is WELL-0001 producing?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert data["details"]["llm_synthesized"] is True
    assert data["details"]["llm_provider"] == "mock"
    assert "INS-0001-0203" in data["answer"]
    assert "15.0°C" in data["answer"]
    assert len(mock.calls) == 1
    # Verify evidence objects were preserved
    assert len(data["evidence"]) >= 1
    assert data["evidence"][0]["inspection_id"] == "INS-0001-0203"


# ---------------------------------------------------------------------------
# 3. Provider error and timeout use the safe fallback
# ---------------------------------------------------------------------------


def test_provider_error_uses_fallback(monkeypatch):
    mock = MockProvider(raise_error=RuntimeError("External LLM API 500 internal server error"))
    monkeypatch.setattr("app.llm_synthesis.get_llm_provider", lambda cfg=None: mock)

    response = client.post(
        "/api/assistant/ask",
        json={"question": "Is WELL-0001 producing?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    # Fallback response preserved
    assert "not producing" in data["answer"].lower()
    assert not data.get("details", {}).get("llm_synthesized", False)


def test_provider_timeout_uses_fallback(monkeypatch):
    mock = MockProvider(raise_error=httpx.TimeoutException("Read timed out after 10.0s"))
    monkeypatch.setattr("app.llm_synthesis.get_llm_provider", lambda cfg=None: mock)

    response = client.post(
        "/api/assistant/ask",
        json={"question": "What was the estimated downtime for WELL-0001 in 2025?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert "21 days" in data["answer"]
    assert not data.get("details", {}).get("llm_synthesized", False)


# ---------------------------------------------------------------------------
# 4. Unsupported questions remain unsupported
# ---------------------------------------------------------------------------


def test_unsupported_questions_remain_unsupported(monkeypatch):
    mock = MockProvider(response_text="The capital of Australia is Canberra.")
    monkeypatch.setattr("app.llm_synthesis.get_llm_provider", lambda cfg=None: mock)

    response = client.post(
        "/api/assistant/ask",
        json={"question": "What is the capital of Australia?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unsupported"
    assert data["evidence"] == []
    # Provider must NOT have been called for unsupported question
    assert len(mock.calls) == 0


# ---------------------------------------------------------------------------
# 5. Citations cannot reference nonexistent evidence
# ---------------------------------------------------------------------------


def test_citations_cannot_reference_nonexistent_evidence(monkeypatch):
    # Model hallucinates a fake inspection ID "INS-9999-9999" and a fake document "fake_sop.md"
    mock = MockProvider(
        response_text=(
            "According to fake_sop.md and inspection INS-9999-9999, the well is operating normally."
        )
    )
    monkeypatch.setattr("app.llm_synthesis.get_llm_provider", lambda cfg=None: mock)

    response = client.post(
        "/api/assistant/ask",
        json={"question": "Is WELL-0001 producing?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    # Unverified citation rejected! Baseline answer used
    assert "INS-9999-9999" not in data["answer"]
    assert not data.get("details", {}).get("llm_synthesized", False)


def test_validate_citations_unit():
    evidence = [
        {"record_id": "MNT-0001-002", "source": "sample-data/assets/WELL-0001/maintenance-reports/MNT-0001-002.md", "excerpt": "Pressure tested under WS-05."},
        {"inspection_id": "INS-0001-0203", "source": "sample-data/assets/WELL-0001/inspections.jsonl"},
    ]
    conflicts = []
    details = {}

    # Valid citations
    valid_text = "Work was completed under MNT-0001-002 and protocol WS-05 according to MNT-0001-002.md."
    is_valid, invalid = validate_citations(valid_text, evidence, conflicts, details)
    assert is_valid is True
    assert invalid == []

    # Invalid citation
    invalid_text = "Refer to report MNT-9999-888 and protocol WS-99."
    is_valid, invalid = validate_citations(invalid_text, evidence, conflicts, details)
    assert is_valid is False
    assert "MNT-9999-888" in invalid or "WS-99" in invalid


# ---------------------------------------------------------------------------
# 6. Contradictory evidence remains disclosed
# ---------------------------------------------------------------------------


def test_contradictory_evidence_remains_disclosed(monkeypatch):
    # For a question where conflicts exist, verify synthesis prompt includes conflicts
    mock = MockProvider(
        response_text=(
            "Wellhead ratings differ between models: T200 is rated at 3,000 psi while T350 is rated at 5,000 psi. "
            "Note the operational discrepancy between these two wellhead specifications."
        )
    )
    monkeypatch.setattr("app.llm_synthesis.get_llm_provider", lambda cfg=None: mock)

    response = client.post(
        "/api/assistant/ask",
        json={"question": "What is the wellhead rating difference between T200 and T350?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    assert len(data["conflicts"]) >= 1
    assert data["details"]["llm_synthesized"] is True
    # Verify conflicts were passed into prompt
    assert len(mock.calls) == 1
    assert "DISCLOSED CONFLICTS & CORRECTIONS" in mock.calls[0]["user_prompt"]


# ---------------------------------------------------------------------------
# 7. Deterministic results cannot be altered by model
# ---------------------------------------------------------------------------


def test_deterministic_production_result_not_altered_by_model(monkeypatch):
    # Baseline for WELL-0001 is "not producing". Model attempts to claim "The well is producing".
    mock = MockProvider(
        response_text="Based on inspection INS-0001-0203, the well is producing normally at full rate."
    )
    monkeypatch.setattr("app.llm_synthesis.get_llm_provider", lambda cfg=None: mock)

    response = client.post(
        "/api/assistant/ask",
        json={"question": "Is WELL-0001 producing?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    # Contradiction rejected! Baseline preserved
    assert "not producing" in data["answer"].lower()
    assert not data.get("details", {}).get("llm_synthesized", False)


def test_deterministic_maintenance_rca_not_altered_by_model(monkeypatch):
    # Baseline for WELL-0001 requires an RCA. Model attempts to claim "does not require an RCA".
    mock = MockProvider(
        response_text="Well WELL-0001 does not require a root-cause analysis (RCA) at this time."
    )
    monkeypatch.setattr("app.llm_synthesis.get_llm_provider", lambda cfg=None: mock)

    response = client.post(
        "/api/assistant/ask",
        json={"question": "Does WELL-0001 require a root-cause analysis?", "asset_id": "WELL-0001"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "answered"
    # Contradiction rejected! Baseline preserved
    assert "requires a root-cause analysis (rca)" in data["answer"].lower()
    assert not data.get("details", {}).get("llm_synthesized", False)


# ---------------------------------------------------------------------------
# 8. Provider implementations & HTTP payload construction
# ---------------------------------------------------------------------------


def test_gemini_provider_generate(monkeypatch):
    def mock_post(url, headers, json):
        assert "x-goog-api-key" in headers
        assert headers["x-goog-api-key"] == "test-gemini-key"
        assert "contents" in json
        assert "system_instruction" in json
        mock_resp = httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": "Synthesized response from Gemini."}]
                        }
                    }
                ]
            },
            request=httpx.Request("POST", url),
        )
        return mock_resp

    monkeypatch.setattr("httpx.Client.post", lambda self, url, headers=None, json=None: mock_post(url, headers, json))

    provider = GeminiProvider(api_key="test-gemini-key", model="gemini-2.5-flash")
    result = provider.generate("system instructions", "user prompt")
    assert result == "Synthesized response from Gemini."


def test_openai_provider_generate(monkeypatch):
    def mock_post(url, headers, json):
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-openai-key"
        assert json["model"] == "gpt-4o-mini"
        assert len(json["messages"]) == 2
        mock_resp = httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Synthesized response from OpenAI.",
                        }
                    }
                ]
            },
            request=httpx.Request("POST", url),
        )
        return mock_resp

    monkeypatch.setattr("httpx.Client.post", lambda self, url, headers=None, json=None: mock_post(url, headers, json))

    provider = OpenAIProvider(api_key="test-openai-key", model="gpt-4o-mini")
    result = provider.generate("system instructions", "user prompt")
    assert result == "Synthesized response from OpenAI."


# ---------------------------------------------------------------------------
# 9. Configuration environment variable reading
# ---------------------------------------------------------------------------


def test_llm_config_environment_parsing(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-12345")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "15.5")

    cfg = get_llm_config()
    assert cfg.enabled is True
    assert cfg.provider == "openai"
    assert cfg.api_key == "sk-proj-12345"
    assert cfg.model == "gpt-4o"
    assert cfg.timeout_seconds == 15.5
