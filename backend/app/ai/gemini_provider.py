import logging
import httpx
from typing import Dict, Any

from app.ai.base import BaseAIProvider
from app.models import LeadInput, AIStructuredOutput

logger = logging.getLogger("gemini_provider")


class GeminiProvider(BaseAIProvider):
    """
    AI Provider implementation for Google Gemini models (Gemini 1.5 Flash, Gemini 1.5 Pro).
    """

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash", timeout: float = 8.0):
        super().__init__(model_name=model_name, timeout=timeout)
        self.api_key = api_key
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"

    @property
    def provider_name(self) -> str:
        return f"google_gemini ({self.model_name})"

    async def generate_lead_analysis(self, lead: LeadInput) -> AIStructuredOutput:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured or is empty.")

        prompt = self.build_prompt(lead)
        url = f"{self.base_url}?key={self.api_key}"

        payload: Dict[str, Any] = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2
            }
        }

        logger.info("Dispatching request to Google Gemini API (model: %s)...", self.model_name)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        try:
            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError("No candidate generation returned from Gemini API.")
            raw_text = candidates[0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise ValueError(f"Malformed response structure from Gemini API: {data}") from exc

        return self.parse_and_validate_json(raw_text)
