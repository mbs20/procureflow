from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Application Settings
    app_name: str = "ProcureFlow OSS"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = True
    secret_key: str = "dev_secret_key_change_in_production_32chars_min"
    api_key: str = "procureflow_dev_api_key_12345"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # Database URLs
    # Defaults to SQLite async for zero-dependency local development, PostgreSQL in Docker/production
    database_url: str = Field(
        default="sqlite+aiosqlite:///./procureflow.db",
        alias="DATABASE_URL",
    )
    database_url_sync: str = Field(
        default="sqlite:///./procureflow.db",
        alias="DATABASE_URL_SYNC",
    )

    # Redis & Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    celery_always_eager: bool = False

    # File Storage
    storage_backend: Literal["local", "s3"] = "local"
    storage_local_dir: str = "./data/storage"
    max_upload_size_bytes: int = 50 * 1024 * 1024  # 50 MB

    # AI / LLM Configuration
    llm_provider: Literal["openai", "anthropic", "ollama", "mock"] = Field(
        default="openai",
        alias="PROCUREFLOW_LLM_PROVIDER",
    )
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # External APIs
    exchange_rate_api_url: str = "https://open.er-api.com/v6/latest"


@lru_cache
def get_settings() -> Settings:
    return Settings()
