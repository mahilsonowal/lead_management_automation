import asyncio
import logging
from typing import Optional

from app.config import settings
from app.models import LeadInput, LeadAnalysisResponse, AIStructuredOutput
from app.scorer import analyze_lead_rules
from app.ai.base import BaseAIProvider
from app.ai.gemini_provider import GeminiProvider
from app.ai.openai_provider import OpenAIProvider
from app.ai.ollama_provider import OllamaProvider

logger = logging.getLogger("ai_manager")


class LeadAnalysisManager:
    """
    Orchestrates lead analysis by coordinating AI providers, retries,
    timeouts, and seamless fallback to deterministic rule-based scoring.
    """

    def __init__(self):
        self.settings = settings

    def get_provider(self) -> Optional[BaseAIProvider]:
        provider_type = self.settings.AI_PROVIDER.lower().strip()

        if provider_type in ["none", "", "rules", "rule_based"]:
            return None

        if provider_type == "gemini":
            if not self.settings.GEMINI_API_KEY:
                logger.warning("AI_PROVIDER is set to 'gemini', but GEMINI_API_KEY is empty. Falling back to rules.")
                return None
            return GeminiProvider(
                api_key=self.settings.GEMINI_API_KEY,
                model_name=self.settings.GEMINI_MODEL,
                timeout=self.settings.AI_TIMEOUT_SECONDS
            )

        if provider_type == "openai":
            if not self.settings.OPENAI_API_KEY:
                logger.warning("AI_PROVIDER is set to 'openai', but OPENAI_API_KEY is empty. Falling back to rules.")
                return None
            return OpenAIProvider(
                api_key=self.settings.OPENAI_API_KEY,
                model_name=self.settings.OPENAI_MODEL,
                timeout=self.settings.AI_TIMEOUT_SECONDS
            )

        if provider_type == "ollama":
            return OllamaProvider(
                base_url=self.settings.OLLAMA_BASE_URL,
                model_name=self.settings.OLLAMA_MODEL,
                timeout=self.settings.AI_TIMEOUT_SECONDS
            )

        logger.warning("Unknown AI_PROVIDER '%s'. Falling back to rules.", provider_type)
        return None

    async def analyze_lead(self, lead: LeadInput) -> LeadAnalysisResponse:
        provider = self.get_provider()

        # If no AI provider is configured, use deterministic rule-based scoring
        if provider is None:
            rule_result = analyze_lead_rules(lead)
            rule_result.analysis_mode = "rule_based"
            rule_result.provider = "rule_engine"
            return rule_result

        # Execute AI analysis with retry loop and timeout handling
        max_attempts = max(1, self.settings.AI_MAX_RETRIES + 1)
        last_error_message = "Unknown error"

        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(
                    "Executing lead analysis via %s (Attempt %d/%d)...",
                    provider.provider_name, attempt, max_attempts
                )
                ai_output: AIStructuredOutput = await provider.generate_lead_analysis(lead)

                # Return successful AI analysis response
                return LeadAnalysisResponse(
                    classification=ai_output.classification,
                    score=ai_output.score,
                    service_requested=ai_output.requested_service,
                    next_action=ai_output.next_action,
                    reply=ai_output.suggested_reply,
                    suggested_reply=ai_output.suggested_reply,
                    confidence=ai_output.confidence,
                    analysis_mode="ai",
                    provider=provider.provider_name
                )
            except Exception as exc:
                last_error_message = str(exc)
                logger.warning(
                    "Attempt %d/%d failed for %s: %s",
                    attempt, max_attempts, provider.provider_name, last_error_message
                )
                if attempt < max_attempts:
                    await asyncio.sleep(self.settings.AI_RETRY_DELAY_SECONDS * attempt)

        # Fallback to deterministic scoring if all AI attempts fail
        logger.error(
            "All AI attempts exhausted for %s (Error: %s). Activating deterministic fallback scoring.",
            provider.provider_name, last_error_message
        )
        fallback_result = analyze_lead_rules(lead)
        fallback_result.analysis_mode = "rule_based_fallback"
        fallback_result.provider = f"{provider.provider_name} (fallback: rule_engine)"
        fallback_result.confidence = 0.85
        return fallback_result


ai_manager = LeadAnalysisManager()
