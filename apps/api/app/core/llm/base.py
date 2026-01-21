from abc import ABC, abstractmethod
from typing import Any, Mapping


class LLMClient(ABC):
    """
    Minimal interface for an LLM client.

    Concrete implementations (dummy, Ollama, OpenAI, etc.) will implement
    this interface. The goal is to keep the rest of the codebase decoupled
    from any specific provider's API.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...

    @abstractmethod
    async def generate(
        self,
        *,
        prompt: str,
        options: Mapping[str, Any] | None = None,
    ) -> str:
        """
        Generate a single text completion given a prompt.

        'options' can carry provider-specific knobs (temperature, max_tokens,
        top_p, etc.). Implementations should treat unknown options leniently.
        """
        ...
