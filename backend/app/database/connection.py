"""
Database connection management.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.debug,
)

readonly_engine = create_async_engine(
    settings.database_readonly_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=settings.debug,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
readonly_session = async_sessionmaker(readonly_engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


async def get_readonly_db() -> AsyncSession:
    async with readonly_session() as session:
        yield session


def _convert_params(params: dict) -> dict:
    from datetime import date as date_type
    cleaned = {}
    for key, value in (params or {}).items():
        if isinstance(value, str):
            try:
                cleaned[key] = date_type.fromisoformat(value)
            except (ValueError, TypeError):
                cleaned[key] = value
        else:
            cleaned[key] = value
    return cleaned


async def execute_query(query_str: str, params: dict = None) -> list[dict]:
    cleaned_params = _convert_params(params or {})
    async with async_session() as session:
        result = await session.execute(text(query_str), cleaned_params)
        columns = result.keys()
        rows = result.fetchall()
        return [dict(zip(columns, row)) for row in rows]


async def execute_readonly_query(query_str: str, params: dict = None, limit: int = 10000) -> list[dict]:
    cleaned = query_str.strip().upper()
    if not cleaned.startswith("SELECT"):
        raise ValueError("Only SELECT queries are permitted on the readonly connection")
    if "LIMIT" not in cleaned:
        query_str = f"{query_str.rstrip(';')} LIMIT {limit}"
    cleaned_params = _convert_params(params or {})
    async with readonly_session() as session:
        result = await session.execute(text(query_str), cleaned_params)
        columns = result.keys()
        rows = result.fetchall()
        return [dict(zip(columns, row)) for row in rows]
