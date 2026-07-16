"""Configuracao central da aplicacao via pydantic-settings."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "credit-analysis-engine"
    app_env: str = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    # LLM
    # Provedor usado quando llm_use_stub=false: "azure" ou "anthropic".
    llm_provider: str = "azure"
    llm_use_stub: bool = True

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_deployment: str = "gpt-4o"

    # Anthropic (Claude) - alternativa ao Azure
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-8"

    # Postgres
    database_url: str = "postgresql+psycopg2://credit:credit@localhost:5432/credit_engine"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Rules
    rules_dir: str = "app/engine/rules"

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
