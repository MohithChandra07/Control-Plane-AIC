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


def normalize_database_url(url: str | None) -> str:
    if not url:
        return DEFAULT_DATABASE_URL
    if url.startswith("sqlite+aiosqlite:///") and not url.startswith("sqlite+aiosqlite:////"):
        rel_path = url[len("sqlite+aiosqlite:///") :]
        abs_path = (_ROOT / rel_path).resolve()
        return f"sqlite+aiosqlite:///{abs_path}"
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]
    if "sslmode=" in url:
        url = (
            url.replace("sslmode=require", "ssl=require")
            .replace("sslmode=prefer", "ssl=prefer")
            .replace("sslmode=disable", "ssl=disable")
        )
    return url


def get_database_url() -> str:
    return normalize_database_url(os.environ.get("DATABASE_URL"))


def get_engine(database_url: str | None = None) -> AsyncEngine:
    norm_url = normalize_database_url(database_url or get_database_url())
    connect_args = {}
    if "asyncpg" in norm_url and "localhost" not in norm_url and "127.0.0.1" not in norm_url:
        connect_args["ssl"] = "require"
    return create_async_engine(norm_url, pool_pre_ping=True, connect_args=connect_args)


def get_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_models(engine: AsyncEngine) -> None:
    """Create tables if they don't exist. Used by tests and local dev;
    production deployments apply ledger/schema.sql explicitly instead."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
