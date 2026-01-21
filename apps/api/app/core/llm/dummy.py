from typing import Any, Mapping

from .base import LLMClient


class DummyLLMClient(LLMClient):
    """
    Dev/test implementation of LLMClient that does not call any real model.

    Useful for:
    - unit tests
    - local dev when you don't want to run Ollama or pay for API calls
    """

    def __init__(self, model: str = "dummy-model") -> None:
        self._model = model

    @property
    def provider_name(self) -> str:
        return "dummy"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self,
        *,
        prompt: str,
        options: Mapping[str, Any] | None = None,
    ) -> str:
        # Simple echo-style behavior for now.
        # We can make this more sophisticated later (e.g. pattern-based responses).
        snippet = prompt.strip()
        if len(snippet) > 200:
            snippet = snippet[:200] + "…"

        return (
            f"[dummy completion from {self.provider_name}:{self.model_name}] "
            f"Prompt snippet: {snippet}"
        )
