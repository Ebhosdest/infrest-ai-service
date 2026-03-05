"""
Application configuration.
Loads from .env file. Change LLM_PROVIDER to switch between openai and anthropic.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://infrest:infrest_dev_2025@localhost:5432/infrest_erp"
    database_readonly_url: str = "postgresql+asyncpg://infrest:infrest_dev_2025@localhost:5432/infrest_erp"

    llm_provider: str = "openai"
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    redis_url: str = "redis://localhost:6379/0"

    service_port: int = 8090
    service_host: str = "0.0.0.0"
    debug: bool = True
    log_level: str = "INFO"

    rate_limit_per_minute: int = 15
    cors_origins: str = "http://localhost:3000,http://localhost:4200,http://localhost:5173"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
