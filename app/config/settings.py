"""Configuração centralizada da aplicação via variáveis de ambiente.

Em produção, os segredos devem ser injetados a partir do Azure Key Vault
(via CSI driver, App Configuration ou variáveis de ambiente do pipeline).
"""
from functools import lru_cache

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Aplicação
    app_env: str = Field(default="development", alias="APP_ENV")
    app_name: str = Field(default="credit-engine", alias="APP_NAME")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Segurança
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=60, alias="JWT_EXPIRE_MINUTES")

    # Seleção de provedor de LLM ("azure" | "anthropic")
    llm_provider: str = Field(default="azure", alias="LLM_PROVIDER")

    # Anthropic (Claude) — provedor alternativo
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_model_principal: str = Field(
        default="claude-sonnet-5", alias="ANTHROPIC_MODEL_PRINCIPAL"
    )
    anthropic_model_fallback: str = Field(
        default="claude-opus-4-8", alias="ANTHROPIC_MODEL_FALLBACK"
    )
    anthropic_max_tokens: int = Field(default=4096, alias="ANTHROPIC_MAX_TOKENS")
    anthropic_max_retries: int = Field(default=3, alias="ANTHROPIC_MAX_RETRIES")
    anthropic_timeout_seconds: int = Field(default=60, alias="ANTHROPIC_TIMEOUT_SECONDS")

    # Azure OpenAI
    azure_openai_endpoint: str = Field(alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(alias="AZURE_OPENAI_API_KEY")
    azure_openai_api_version: str = Field(default="2024-10-21", alias="AZURE_OPENAI_API_VERSION")
    azure_openai_deployment_gpt41: str = Field(alias="AZURE_OPENAI_DEPLOYMENT_GPT41")
    azure_openai_deployment_gpt41_mini: str = Field(alias="AZURE_OPENAI_DEPLOYMENT_GPT41_MINI")
    azure_openai_deployment_embeddings: str = Field(alias="AZURE_OPENAI_DEPLOYMENT_EMBEDDINGS")
    azure_openai_max_retries: int = Field(default=3, alias="AZURE_OPENAI_MAX_RETRIES")
    azure_openai_timeout_seconds: int = Field(default=60, alias="AZURE_OPENAI_TIMEOUT_SECONDS")

    # Persistência
    database_url: PostgresDsn = Field(alias="DATABASE_URL")
    redis_url: RedisDsn = Field(alias="REDIS_URL")


@lru_cache
def get_settings() -> Settings:
    """Retorna instância única de Settings (cacheada por processo)."""
    return Settings()  # type: ignore[call-arg]
