from typing import Any, Mapping

import httpx

from app.core.config import get_settings

from .base import LLMClient


class OllamaLLMClient(LLMClient):
    """
    LLMClient implementation for a local Ollama instance.

    Expects an Ollama server running (by default) on http://localhost:11434.

    API reference (simplified):
    - POST /api/generate
      { "model": "...", "prompt": "...", "stream": false }
    """

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self,
        *,
        prompt: str,
        options: Mapping[str, Any] | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
        }

        # Allow some basic knobs via options without being too strict.
        if options:
            temperature = options.get("temperature")
            if isinstance(temperature, (int, float)):
                payload["temperature"] = float(temperature)

            num_predict = options.get("max_tokens") or options.get("num_predict")
            if isinstance(num_predict, int):
                payload["num_predict"] = num_predict

        url = f"{self._base_url}/api/generate"

        # Simple async request to Ollama
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(url, json=payload)
            res.raise_for_status()
            data = res.json()

        # For non-streaming, Ollama returns a single JSON with a 'response' field.
        response_text = data.get("response", "")
        if not isinstance(response_text, str):
            response_text = str(response_text)

        return response_text
