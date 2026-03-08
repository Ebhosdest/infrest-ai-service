"""
Application configuration.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
import os


def _fix_db_url(url: str) -> str:
    if not url:
        return url
    url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if "postgresql+asyncpg+asyncpg" in url:
        url = url.replace("postgresql+asyncpg+asyncpg", "postgresql+asyncpg")
    return url


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://infrest:infrest_dev_2025@localhost:5432/infrest_erp"
    database_readonly_url: str = "postgresql+asyncpg://infrest:infrest_dev_2025@localhost:5432/infrest_erp"
    llm_provider: str = "openai"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    redis_url: str = ""
    service_port: int = 8090
    service_host: str = "0.0.0.0"
    debug: bool = False
    log_level: str = "INFO"
    rate_limit_per_minute: int = 15
    cors_origins: str = "*"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'database_url', _fix_db_url(self.database_url))
        object.__setattr__(self, 'database_readonly_url', _fix_db_url(self.database_readonly_url))

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
