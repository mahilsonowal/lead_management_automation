# pyrefly: ignore [missing-import]
import pytest
import httpx
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.models import LeadInput, AIStructuredOutput
from app.ai.base import BaseAIProvider
from app.ai.manager import LeadAnalysisManager
from app.config import settings

client = TestClient(app)


class MockAIProvider(BaseAIProvider):
    """Mock AI Provider for unit testing."""
    def __init__(self, should_fail: bool = False, raw_response: str = ""):
        super().__init__(model_name="mock-model", timeout=2.0)
        self.should_fail = should_fail
        self.raw_response = raw_response

    @property
    def provider_name(self) -> str:
        return "mock_ai_provider"

    async def generate_lead_analysis(self, lead: LeadInput) -> AIStructuredOutput:
        if self.should_fail:
            raise httpx.ConnectTimeout("Connection to AI service timed out after 2.0s")
        return self.parse_and_validate_json(self.raw_response)


def test_ai_structured_output_normalization():
    """Verify that uppercase or clamped values normalize properly."""
    raw = {
        "classification": "HOT",
        "score": "120",  # Clamped to 100
        "requested_service": "AI & CRM Pipelines",
        "next_action": "Call lead within 10 minutes",
        "suggested_reply": "Hello Rahul, we are ready to assist you right away.",
        "confidence": 0.98
    }
    output = AIStructuredOutput(**raw)
    assert output.classification == "hot"
    assert output.score == 100
    assert output.confidence == 0.98


def test_ai_base_provider_markdown_fence_cleaning():
    """Verify that JSON wrapped in markdown code blocks is stripped and parsed correctly."""
    provider = MockAIProvider()
    raw_markdown = """```json
    {
      "classification": "warm",
      "score": 60,
      "requested_service": "Virtual Assistant Services",
      "next_action": "Send service catalog and portfolio",
      "suggested_reply": "Hello Priya, we would be thrilled to support your operations.",
      "confidence": 0.90
    }
    ```"""
    parsed = provider.parse_and_validate_json(raw_markdown)
    assert parsed.classification == "warm"
    assert parsed.score == 60
    assert parsed.requested_service == "Virtual Assistant Services"


@pytest.mark.anyio
async def test_ai_manager_fallback_on_timeout():
    """Verify that when AI provider times out, system smoothly falls back to rules."""
    lead = LeadInput(
        name="Rahul Das",
        email="rahul@example.com",
        company="North East Digital Agency",
        requested_service="CRM and AI automation",
        message="We urgently need help automating our customer support and lead follow-up process."
    )

    manager = LeadAnalysisManager()
    # Mock provider that always times out
    mock_failing_provider = MockAIProvider(should_fail=True)
    with patch.object(manager, "get_provider", return_value=mock_failing_provider):
        response = await manager.analyze_lead(lead)

        assert response.analysis_mode == "rule_based_fallback"
        assert response.score == 100
        assert response.classification == "hot"
        assert "fallback" in response.provider


@pytest.mark.anyio
async def test_ai_manager_fallback_on_malformed_json():
    """Verify that when AI returns garbage/invalid JSON, system falls back to rules."""
    lead = LeadInput(
        name="Priya Sharma",
        email="priya@example.com",
        company="Bright SaaS",
        requested_service="SaaS operations",
        message="We would like to learn more about improving our onboarding workflow."
    )

    manager = LeadAnalysisManager()
    mock_bad_json_provider = MockAIProvider(should_fail=False, raw_response="Sorry, I cannot help with this request.")
    with patch.object(manager, "get_provider", return_value=mock_bad_json_provider):
        response = await manager.analyze_lead(lead)

        assert response.analysis_mode == "rule_based_fallback"
        assert response.score >= 40
        assert response.classification == "warm"


@pytest.mark.anyio
async def test_ai_manager_successful_ai_response():
    """Verify that a successful AI response is returned with mode='ai'."""
    lead = LeadInput(
        name="Rahul Das",
        email="rahul@example.com",
        company="North East Digital Agency",
        requested_service="CRM and AI automation",
        message="We urgently need help automating our customer support and lead follow-up process."
    )

    valid_json = """{
      "classification": "hot",
      "score": 95,
      "requested_service": "CRM and AI Automation",
      "next_action": "Direct executive callback in 15 mins",
      "suggested_reply": "Hello Rahul, our senior AI specialist will reach out immediately.",
      "confidence": 0.96
    }"""

    manager = LeadAnalysisManager()
    mock_success_provider = MockAIProvider(should_fail=False, raw_response=valid_json)
    with patch.object(manager, "get_provider", return_value=mock_success_provider):
        response = await manager.analyze_lead(lead)

        assert response.analysis_mode == "ai"
        assert response.score == 95
        assert response.classification == "hot"
        assert response.confidence == 0.96
        assert response.suggested_reply == response.reply
