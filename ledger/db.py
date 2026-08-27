"""Async SQLAlchemy engine/session setup.

DATABASE_URL drives the dialect: postgresql+asyncpg://... in production,
sqlite+aiosqlite:///... in tests (see tests/integration/test_gateway_roundtrip.py).
Both are exercised through the same ledger.models.Base metadata.
"""

from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ledger.models import Base

DEFAULT_DATABASE_URL = "postgresql+asyncpg://controlplane:controlplane@localhost:5432/controlplane"


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def get_engine(database_url: str | None = None) -> AsyncEngine:
    return create_async_engine(database_url or get_database_url(), pool_pre_ping=True)


def get_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_models(engine: AsyncEngine) -> None:
    """Create tables if they don't exist. Used by tests and local dev;
    production deployments apply ledger/schema.sql explicitly instead."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
