import json
import re
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any

from app.models import LeadInput, AIStructuredOutput

logger = logging.getLogger("ai_provider")


class BaseAIProvider(ABC):
    """
    Abstract Base Class for all AI model providers (Gemini, OpenAI, Ollama).
    """

    def __init__(self, model_name: str, timeout: float = 8.0):
        self.model_name = model_name
        self.timeout = timeout

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name identifier of the provider."""
        pass

    @abstractmethod
    async def generate_lead_analysis(self, lead: LeadInput) -> AIStructuredOutput:
        """
        Executes AI completion and returns validated AIStructuredOutput.
        Must raise exceptions on network errors, timeouts, or parsing errors.
        """
        pass

    def build_prompt(self, lead: LeadInput) -> str:
        """
        Constructs a structured system and user prompt ensuring strict JSON output.
        """
        return f"""You are an elite Lead Qualification and CRM Automation AI.
Your job is to analyze the following inbound lead inquiry and output ONLY a valid, parseable JSON object.

LEAD DETAILS:
- Full Name: {lead.name}
- Email: {lead.email}
- Company: {lead.company if lead.company else "Not Provided"}
- Requested Service: {lead.requested_service}
- Inquiry Message: {lead.message}

EVALUATION CRITERIA:
1. Classification & Scoring:
   - "hot" (Score 70-100): High urgency keywords (urgent, ASAP, immediately, emergency), well-defined high-value services (AI automation, CRM, custom workflows), established company, or deep project requirements.
   - "warm" (Score 40-69): Clear interest, exploring options, standard business inquiry without extreme urgency.
   - "cold" (Score 0-39): Very brief/vague message, general inquiry, missing company, or generic request.
2. Service Requested: Standardize and clean the service title.
3. Next Action: A concrete, operational next step for the Virtual Assistant or Sales team (e.g. 15-minute callback, send portfolio deck, enroll in nurture sequence).
4. Suggested Reply: A highly professional, warm, and personalized email response draft addressing the lead by their first name and mentioning their exact project needs.
5. Confidence: A float between 0.0 and 1.0 indicating your certainty.

REQUIRED JSON FORMAT (output NOTHING except this valid JSON):
{{
  "classification": "hot" | "warm" | "cold",
  "score": <integer 0-100>,
  "requested_service": "<cleaned service name>",
  "next_action": "<operational next step>",
  "suggested_reply": "<personalized email response draft>",
  "confidence": <float 0.0-1.0>
}}"""

    def parse_and_validate_json(self, raw_text: str) -> AIStructuredOutput:
        """
        Extracts JSON from text (stripping markdown code fences if present)
        and validates with Pydantic AIStructuredOutput.
        """
        cleaned_text = raw_text.strip()

        # Remove markdown code fences if present (e.g. ```json ... ``` or ``` ...)
        if cleaned_text.startswith("```"):
            cleaned_text = re.sub(r"^```(?:json)?\s*", "", cleaned_text, flags=re.IGNORECASE)
            cleaned_text = re.sub(r"\s*```$", "", cleaned_text)
            cleaned_text = cleaned_text.strip()

        # Regex fallback to find the first JSON object if surrounded by preamble
        match = re.search(r"(\{.*\})", cleaned_text, re.DOTALL)
        if match:
            cleaned_text = match.group(1)

        try:
            parsed_data: Dict[str, Any] = json.loads(cleaned_text)
        except json.JSONDecodeError as exc:
            logger.warning("Failed to decode JSON from AI output: %s | Raw: %s", exc, raw_text[:200])
            raise ValueError(f"AI response was not valid JSON: {exc}") from exc

        return AIStructuredOutput(**parsed_data)
