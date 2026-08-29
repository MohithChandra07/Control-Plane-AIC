"""Async SQLAlchemy engine/session setup.

DATABASE_URL drives the dialect: postgresql+asyncpg://... in production,
sqlite+aiosqlite:///... in tests (see tests/integration/test_gateway_roundtrip.py).
Both are exercised through the same ledger.models.Base metadata.
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ledger.models import Base

_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_SQLITE_PATH = _ROOT / "demo" / "replayer" / "traffic.db"
DEFAULT_DATABASE_URL = f"sqlite+aiosqlite:///{_DEFAULT_SQLITE_PATH}"


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        return DEFAULT_DATABASE_URL
    if url.startswith("sqlite+aiosqlite:///") and not url.startswith("sqlite+aiosqlite:////"):
        rel_path = url[len("sqlite+aiosqlite:///") :]
        abs_path = (_ROOT / rel_path).resolve()
        return f"sqlite+aiosqlite:///{abs_path}"
    return url


def get_engine(database_url: str | None = None) -> AsyncEngine:
    return create_async_engine(database_url or get_database_url(), pool_pre_ping=True)


def get_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_models(engine: AsyncEngine) -> None:
    """Create tables if they don't exist. Used by tests and local dev;
    production deployments apply ledger/schema.sql explicitly instead."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
