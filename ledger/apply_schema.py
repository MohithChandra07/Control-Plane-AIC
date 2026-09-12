"""Applies ledger/schema.sql to PostgreSQL via async SQLAlchemy/asyncpg."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import asyncpg

from ledger.db import normalize_database_url


async def apply_schema(url: str | None = None) -> None:
    raw_url = url or os.environ.get("DATABASE_URL", "")
    if not raw_url:
        raise RuntimeError("No database URL provided.")

    # Format URL for asyncpg: postgresql://...
    norm_url = normalize_database_url(raw_url)
    if norm_url.startswith("postgresql+asyncpg://"):
        norm_url = "postgresql://" + norm_url[len("postgresql+asyncpg://") :]

    print(f"Connecting to database: {norm_url.split('@')[-1] if '@' in norm_url else 'local'}...")
    schema_file = Path(__file__).resolve().parent / "schema.sql"
    sql = schema_file.read_text()

    conn = await asyncpg.connect(norm_url, ssl="require" if "localhost" not in norm_url and "127.0.0.1" not in norm_url else None)
    try:
        await conn.execute(sql)
        print("ledger/schema.sql successfully applied.")
    finally:
        await conn.close()


if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DATABASE_URL")
    asyncio.run(apply_schema(target_url))
