from functools import lru_cache

from app.core.config import get_settings

from .base import LLMClient
from .dummy import DummyLLMClient


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    """
    Return a singleton LLM client based on current settings.

    For now, only the 'dummy' provider is implemented. Later we will add
    real implementations for providers like 'ollama' and 'openai'.
    """
    settings = get_settings()
    provider = settings.llm_provider.lower()

    if provider in {"dummy", "dev"}:
        return DummyLLMClient(model=settings.llm_model)

    # Future placeholders (ollama, openai, etc.) will be wired here.
    # Example:
    # if provider == "ollama":
    #     return OllamaLLMClient(base_url=settings.ollama_base_url, model=settings.llm_model)
    # if provider == "openai":
    #     return OpenAIClient(api_key=settings.openai_api_key, model=settings.openai_model)

    raise ValueError(
        f"Unsupported LLM provider: {provider!r}. "
        "Currently only 'dummy' is implemented."
    )
