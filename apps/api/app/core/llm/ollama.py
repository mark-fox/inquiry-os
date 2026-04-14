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
        url = f"{self._base_url}/api/chat"

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": "Follow the user's output format exactly. Do not add extra text.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "stream": False,
        }

        if options:
            if options.get("format") == "json":
                payload["format"] = "json"

            temperature = options.get("temperature")
            if isinstance(temperature, (int, float)):
                payload["options"] = payload.get("options", {})
                payload["options"]["temperature"] = float(temperature)

            max_tokens = options.get("max_tokens")
            if isinstance(max_tokens, int):
                payload["options"] = payload.get("options", {})
                payload["options"]["num_predict"] = max_tokens

        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(url, json=payload)
            res.raise_for_status()
            data = res.json()

        # Chat endpoint response shape
        message = data.get("message", {})
        content = message.get("content", "")

        if not isinstance(content, str):
            content = str(content)

        return content
