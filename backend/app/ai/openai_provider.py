import logging
import httpx
from typing import Dict, Any

from app.ai.base import BaseAIProvider
from app.models import LeadInput, AIStructuredOutput

logger = logging.getLogger("openai_provider")


class OpenAIProvider(BaseAIProvider):
    """
    AI Provider implementation for OpenAI models (GPT-4o, GPT-4o-mini).
    """

    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini", timeout: float = 8.0):
        super().__init__(model_name=model_name, timeout=timeout)
        self.api_key = api_key
        self.endpoint = "https://api.openai.com/v1/chat/completions"

    @property
    def provider_name(self) -> str:
        return f"openai ({self.model_name})"

    async def generate_lead_analysis(self, lead: LeadInput) -> AIStructuredOutput:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured or is empty.")

        prompt = self.build_prompt(lead)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "You are a CRM and lead qualification automation AI that responds only in JSON."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }

        logger.info("Dispatching request to OpenAI API (model: %s)...", self.model_name)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.endpoint, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        try:
            choices = data.get("choices", [])
            if not choices:
                raise ValueError("No completion choices returned from OpenAI API.")
            raw_text = choices[0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise ValueError(f"Malformed response structure from OpenAI API: {data}") from exc

        return self.parse_and_validate_json(raw_text)
