"""Applies ledger/schema.sql to PostgreSQL via async SQLAlchemy/asyncpg."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from sqlalchemy import text

from ledger.db import get_database_url, get_engine


async def apply_schema(url: str | None = None) -> None:
    db_url = url or get_database_url()
    print(f"Connecting to database: {db_url.split('@')[-1] if '@' in db_url else 'local'}...")
    engine = get_engine(db_url)
    schema_file = Path(__file__).resolve().parent / "schema.sql"
    sql = schema_file.read_text()

    async with engine.begin() as conn:
        for stmt in sql.split(";"):
            cleaned = stmt.strip()
            if cleaned:
                await conn.execute(text(cleaned))

    await engine.dispose()
    print("ledger/schema.sql successfully applied.")


if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DATABASE_URL")
    asyncio.run(apply_schema(target_url))
