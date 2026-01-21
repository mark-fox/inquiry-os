from functools import lru_cache

from app.core.config import get_settings

from .base import LLMClient
from .dummy import DummyLLMClient
from .ollama import OllamaLLMClient


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    """
    Return a singleton LLM client based on current settings.

    Supported providers:
    - 'dummy' (or 'dev'): in-memory echo-style client
    - 'ollama': local Ollama server via HTTP

    Future:
    - 'openai' and others can be added here.
    """
    settings = get_settings()
    provider = settings.llm_provider.lower()

    if provider in {"dummy", "dev"}:
        return DummyLLMClient(model=settings.llm_model)

    if provider == "ollama":
        # Use the configured base URL and model name
        return OllamaLLMClient(
            base_url=settings.ollama_base_url,
            model=settings.llm_model,
        )

    raise ValueError(
        f"Unsupported LLM provider: {provider!r}. "
        "Currently supported: 'dummy', 'ollama'."
    )
