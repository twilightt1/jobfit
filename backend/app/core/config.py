from collections.abc import Sequence
from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    database_url: str = Field(
        default="postgresql+asyncpg://jobfit:jobfit@localhost:5432/jobfit",
        alias="DATABASE_URL",
    )
    sync_database_url: str = Field(
        default="postgresql+psycopg://jobfit:jobfit@localhost:5432/jobfit",
        alias="SYNC_DATABASE_URL",
    )
    backend_cors_origins: str | list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        alias="BACKEND_CORS_ORIGINS",
    )

    # AI / LLM providers. Default to "local" so the repo runs with no API key.
    # "openai" enables the OpenAI-compatible client (works with OpenAI, Gemini's
    # OpenAI-compat endpoint, Ollama, vLLM, OpenRouter, LM Studio, etc.).
    ai_provider: str = Field(default="local", alias="AI_PROVIDER")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")

    # OpenAI-compatible Chat Completions endpoint. Point at any compatible base URL.
    # Examples:
    #   OpenAI:        https://api.openai.com/v1
    #   Gemini compat: https://generativelanguage.googleapis.com/v1beta/openai
    #   Ollama local:  http://localhost:11434/v1
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    llm_temperature: float = Field(default=0.0, alias="LLM_TEMPERATURE")
    llm_request_timeout_seconds: float = Field(default=30.0, alias="LLM_REQUEST_TIMEOUT_SECONDS")
    llm_max_repair_attempts: int = Field(default=2, alias="LLM_MAX_REPAIR_ATTEMPTS")

    embedding_provider: str = Field(default="local", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="EMBEDDING_MODEL",
    )
    embedding_dimension: int = Field(default=384, alias="EMBEDDING_DIMENSION")

    upload_storage_dir: str = Field(default="storage/uploads", alias="UPLOAD_STORAGE_DIR")
    max_upload_bytes: int = Field(default=10_000_000, alias="MAX_UPLOAD_BYTES")
    url_fetch_timeout_seconds: float = Field(default=10.0, alias="URL_FETCH_TIMEOUT_SECONDS")
    max_url_response_bytes: int = Field(default=2_000_000, alias="MAX_URL_RESPONSE_BYTES")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | Sequence[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return list(value)

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_async_database_url(cls, value: Any) -> Any:
        if isinstance(value, str):
            if value.startswith("postgres://"):
                return value.replace("postgres://", "postgresql+asyncpg://", 1)
            if value.startswith("postgresql://"):
                return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @field_validator("sync_database_url", mode="before")
    @classmethod
    def normalize_sync_database_url(cls, value: Any) -> Any:
        if isinstance(value, str):
            if value.startswith("postgres://"):
                return value.replace("postgres://", "postgresql+psycopg://", 1)
            if value.startswith("postgresql://"):
                return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
