from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_database_url(cls, v: str) -> str:
        if v and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
    REDIS_URL: str
    JWT_SECRET_KEY: str
    ENVIRONMENT: str = "development"

    # LLM providers — set at least one
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""

    # Primary provider hint (informational; Router uses all configured keys)
    LLM_PROVIDER: str = "openai"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def active_providers(self) -> list[str]:
        """Returns the list of providers that have a non-empty API key."""
        providers = []
        if self.OPENAI_API_KEY:
            providers.append("openai")
        if self.ANTHROPIC_API_KEY:
            providers.append("anthropic")
        if self.GROQ_API_KEY:
            providers.append("groq")
        if self.OPENROUTER_API_KEY:
            providers.append("openrouter")
        return providers


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
