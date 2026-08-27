from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/semantic_code"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "code_embeddings"

    embedding_provider: str = "gemini"
    embedding_model: str = "text-embedding-004"
    embedding_dimensions: int = 768
    ollama_embedding_model: str = "nomic-embed-text"

    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    openai_api_key: str = ""
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "gemma2:4b"

    browse_root: str = "/host/users"

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()


BROWSE_ROOT = get_settings().browse_root


_active_llm_provider: str | None = None
_active_embedding_provider: str | None = None


def get_active_llm_provider() -> str:
    if _active_llm_provider is not None:
        return _active_llm_provider
    return get_settings().llm_provider


def set_active_llm_provider(provider: str) -> None:
    global _active_llm_provider  # noqa: PLW0603
    _active_llm_provider = provider.lower()


def get_active_embedding_provider() -> str:
    if _active_embedding_provider is not None:
        return _active_embedding_provider
    return get_settings().embedding_provider


def set_active_embedding_provider(provider: str) -> None:
    global _active_embedding_provider  # noqa: PLW0603
    _active_embedding_provider = provider.lower()
