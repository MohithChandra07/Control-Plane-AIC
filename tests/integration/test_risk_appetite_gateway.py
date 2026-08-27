"""Proves risk appetite is a real, working control (spec §20: "not a
cosmetic slider") -- setting it in tenant_settings measurably changes
what the gateway does with the exact same input, with no gateway
restart."""

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from gateway.main import create_app
from gateway.providers.base import Provider
from ledger.db import get_sessionmaker
from ledger.models import TenantSetting

# A single-digit claim: contradicts the corpus (real value is 5-7 days)
# but only weakly, near the low end of a typical tier1_trigger -- a good
# probe for whether Tier 1 fires at all.
BORDERLINE_CONTENT = "Refund processing takes 2 business days after approval."


class FakeProvider(Provider):
    def __init__(self, content: str):
        self._content = content

    async def chat_completion(self, payload):
        return {
            "id": "chatcmpl-fake",
            "object": "chat.completion",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": self._content}, "finish_reason": "stop"}],
        }


def _sqlite_engine(db_path: Path):
    return create_async_engine(f"sqlite+aiosqlite:///{db_path}")


async def _set_appetite(engine, tenant_id: str, appetite: float) -> None:
    sessionmaker = get_sessionmaker(engine)
    async with sessionmaker() as session:
        session.add(TenantSetting(tenant_id=tenant_id, risk_appetite=appetite, updated_by="test"))
        await session.commit()


def test_low_appetite_relaxes_tier1_gate(tmp_path):
    import asyncio

    db_path = tmp_path / "audit.db"
    engine = _sqlite_engine(db_path)
    app = create_app(provider=FakeProvider(BORDERLINE_CONTENT), engine=engine, run_migrations=True)

    with TestClient(app) as client:
        # internal_copilot: tier1_trigger=0.5 by default; a single digit
        # ("2") scores 0.45 in quick_risk_score -- just under, Tier 0 only.
        baseline = client.post(
            "/v1/chat/completions",
            json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
            headers={"x-controlplane-tenant": "internal_copilot"},
        ).json()
        assert baseline["controlplane"]["tier"] == 0

        asyncio.run(_set_appetite(engine, "internal_copilot", 1.0))  # strictest

        strict = client.post(
            "/v1/chat/completions",
            json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
            headers={"x-controlplane-tenant": "internal_copilot"},
        ).json()

    # Same input, same tenant, no restart -- only the live appetite
    # setting changed, and that alone flipped Tier 1 on.
    assert strict["controlplane"]["tier"] == 1


def test_appetite_setting_persists(tmp_path):
    import asyncio

    db_path = tmp_path / "audit.db"
    engine = _sqlite_engine(db_path)
    app = create_app(provider=FakeProvider("hello"), engine=engine, run_migrations=True)

    with TestClient(app):
        pass  # just runs migrations via lifespan

    asyncio.run(_set_appetite(engine, "customer_support", 0.9))

    async def _fetch():
        sessionmaker = get_sessionmaker(engine)
        async with sessionmaker() as session:
            rows = (await session.execute(select(TenantSetting))).scalars().all()
            return rows

    rows = asyncio.run(_fetch())
    assert len(rows) == 1
    assert rows[0].risk_appetite == 0.9
    # Writing the setting itself is not, on its own, an audit_events row
    # in this test (that happens in console/backend/main.py's write
    # endpoint, exercised in tests/integration/test_console_backend.py) --
    # this test only proves the settings table itself persists correctly.
