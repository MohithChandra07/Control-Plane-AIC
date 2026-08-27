"""End-to-end Scenes 1-3 (spec §15) through the real gateway: real
GovernanceEngine (real corpus, real regex PII detector, real heuristic
claim verifier), fake upstream provider so no real LLM call is made.
"""

import asyncio
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from gateway.main import create_app
from gateway.providers.base import Provider
from ledger.audit import verify_chain
from ledger.db import get_sessionmaker
from ledger.models import AuditEvent


class FakeProvider(Provider):
    def __init__(self, content: str):
        self._content = content

    async def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": "chatcmpl-fake",
            "object": "chat.completion",
            "choices": [
                {"index": 0, "message": {"role": "assistant", "content": self._content}, "finish_reason": "stop"}
            ],
        }


def _sqlite_engine(db_path: Path):
    return create_async_engine(f"sqlite+aiosqlite:///{db_path}")


async def _fetch_audit_events(db_path: Path) -> list[AuditEvent]:
    engine = _sqlite_engine(db_path)
    sessionmaker = get_sessionmaker(engine)
    async with sessionmaker() as session:
        result = await session.execute(select(AuditEvent).order_by(AuditEvent.id))
        events = list(result.scalars().all())
    await engine.dispose()
    return events


def _post(app, tenant: str = "customer_support"):
    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hi"}]},
            headers={"x-controlplane-tenant": tenant},
        )
    return response


def test_scene1_clean_query_has_low_overhead(tmp_path):
    db_path = tmp_path / "audit.db"
    app = create_app(
        provider=FakeProvider("Thanks for reaching out! How can I help you today?"),
        engine=_sqlite_engine(db_path),
        run_migrations=True,
    )

    response = _post(app)
    assert response.status_code == 200
    body = response.json()
    assert body["choices"][0]["message"]["content"] == "Thanks for reaching out! How can I help you today?"
    assert body["controlplane"]["decision"] == "ALLOW"
    assert body["controlplane"]["tier"] == 0
    assert body["controlplane"]["claims"] == []

    events = asyncio.run(_fetch_audit_events(db_path))
    assert len(events) == 1  # request-level row only -- no claims were extracted
    assert verify_chain(events) is True


def test_scene2_fabricated_clause_is_surgically_removed(tmp_path):
    db_path = tmp_path / "audit.db"
    app = create_app(
        provider=FakeProvider(
            "Refunds are available within 30 days. "
            "Refunds are issued to the original payment method. "
            "Your refund processing will definitely take 2 hours."
        ),
        engine=_sqlite_engine(db_path),
        run_migrations=True,
    )

    response = _post(app)
    assert response.status_code == 200
    body = response.json()
    content = body["choices"][0]["message"]["content"]

    assert "30 days" in content
    assert "original payment method" in content
    assert "2 hours" not in content  # the fabricated claim, not the whole response
    assert body["controlplane"]["decision"] in ("ESCALATE", "MODIFY")
    assert body["controlplane"]["tier"] == 1
    assert len(body["controlplane"]["claims"]) == 3

    events = asyncio.run(_fetch_audit_events(db_path))
    assert len(events) == 1 + 3  # request-level row + one per claim
    assert verify_chain(events) is True
    claim_rows = [e for e in events if e.claim_id is not None]
    verdicts = {row.verdict for row in claim_rows}
    assert "SUPPORTED" in verdicts
    assert "CONTRADICTED" in verdicts


def test_scene3_invented_phone_number_is_hallucination_and_pii(tmp_path):
    db_path = tmp_path / "audit.db"
    app = create_app(
        provider=FakeProvider("The customer's phone number is 9876543210 according to our records."),
        engine=_sqlite_engine(db_path),
        run_migrations=True,
    )

    response = _post(app)
    assert response.status_code == 200
    body = response.json()
    content = body["choices"][0]["message"]["content"]

    assert "9876543210" not in content
    assert "[REDACTED_PHONE]" in content
    assert body["controlplane"]["decision"] == "MODIFY"
    claim = body["controlplane"]["claims"][0]
    assert set(claim["risk_labels"]) == {"hallucination", "pii"}
    assert claim["verdict"] == "UNVERIFIABLE"  # ungrounded, not proven false -- never CONTRADICTED here

    events = asyncio.run(_fetch_audit_events(db_path))
    claim_row = next(e for e in events if e.claim_id is not None)
    assert claim_row.risk_labels["hallucination"]["detected"] is True
    assert claim_row.risk_labels["pii"]["detected"] is True
    assert verify_chain(events) is True
