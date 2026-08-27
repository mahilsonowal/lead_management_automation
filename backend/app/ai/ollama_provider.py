import logging
import httpx
from typing import Dict, Any

from app.ai.base import BaseAIProvider
from app.models import LeadInput, AIStructuredOutput

logger = logging.getLogger("ollama_provider")


class OllamaProvider(BaseAIProvider):
    """
    AI Provider implementation for local Ollama instances (e.g. llama3.2, mistral, qwen).
    """

    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "llama3.2", timeout: float = 15.0):
        super().__init__(model_name=model_name, timeout=timeout)
        self.base_url = base_url.rstrip("/")
        self.endpoint = f"{self.base_url}/api/generate"

    @property
    def provider_name(self) -> str:
        return f"ollama_local ({self.model_name})"

    async def generate_lead_analysis(self, lead: LeadInput) -> AIStructuredOutput:
        prompt = self.build_prompt(lead)

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.2
            }
        }

        logger.info("Dispatching request to local Ollama service (%s at %s)...", self.model_name, self.base_url)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.endpoint, json=payload)
            response.raise_for_status()
            data = response.json()

        raw_text = data.get("response", "")
        if not raw_text:
            raise ValueError("Empty completion response received from Ollama.")

        return self.parse_and_validate_json(raw_text)
