"""Smoke test for the traffic replayer: proves it runs end-to-end against
an isolated sqlite DB and actually writes audit rows -- not a claim about
throughput at real 10k scale, which is exercised manually (see
docs/roadmap.md for the measured numbers from an actual run)."""

import asyncio
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from demo.replayer.replay import replay
from ledger.db import get_sessionmaker
from ledger.models import AuditEvent


async def _count_events(db_path: Path) -> int:
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    sessionmaker = get_sessionmaker(engine)
    async with sessionmaker() as session:
        result = await session.execute(select(AuditEvent))
        count = len(result.scalars().all())
    await engine.dispose()
    return count


def test_replay_populates_the_audit_ledger(tmp_path, monkeypatch):
    import demo.replayer.replay as replay_module

    db_path = tmp_path / "replay_test.db"
    monkeypatch.setattr(replay_module, "DEFAULT_DB_PATH", db_path)

    summary = replay(count=20, seed=3, database_url=None, progress_every=0)

    assert summary["interactions"] == 20
    assert sum(summary["decision_counts"].values()) == 20
    assert "RATE_LIMITED" not in summary["decision_counts"]  # cost breaker is disabled for this tool

    event_count = asyncio.run(_count_events(db_path))
    assert event_count >= 20  # at least one row per request, plus per-claim rows
