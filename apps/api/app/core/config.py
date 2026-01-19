from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # API metadata
    api_name: str = "InquiryOS API"
    api_version: str = "0.1.0"

    # Server config
    api_port: int = 8000

    # Database (we'll use this later when we add Postgres)
    database_url: str = (
        "postgresql+asyncpg://inquiryos:inquiryos@localhost:5432/inquiryos"
    )

    # LLM provider settings (default to local/open-source via Ollama)
    llm_provider: str = "ollama"  # options later: "ollama", "openai"
    llm_model: str = "llama3"

    # Ollama config
    ollama_base_url: str = "http://localhost:11434"

    # OpenAI config (optional)
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings instance so we don't re-parse env vars on every import.
    """
    return Settings()
