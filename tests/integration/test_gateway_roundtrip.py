import asyncio
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from gateway.main import create_app
from gateway.providers.base import Provider, ProviderError
from ledger.audit import verify_chain
from ledger.db import get_sessionmaker
from ledger.models import AuditEvent

FAKE_UPSTREAM_RESPONSE = {
    "id": "chatcmpl-fake",
    "object": "chat.completion",
    "choices": [
        {
            "index": 0,
            # No digits/PII -> Tier 0 skips governance, so this fixture stays
            # a pure plumbing check. Governance behavior itself is covered in
            # tests/integration/test_gateway_governance.py.
            "message": {"role": "assistant", "content": "Thanks for reaching out! How can I help you today?"},
            "finish_reason": "stop",
        }
    ],
}


class FakeProvider(Provider):
    def __init__(self, response: dict[str, Any] | None = None, error: Exception | None = None):
        self._response = response
        self._error = error
        self.last_payload: dict[str, Any] | None = None

    async def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.last_payload = payload
        if self._error is not None:
            raise self._error
        assert self._response is not None
        return self._response


def _sqlite_engine(db_path: Path):
    # File-backed (not :memory:) so a fresh engine/connection opened *after*
    # the app's TestClient/lifespan has shut down (and disposed its own
    # engine+event-loop-bound connection) can still read what was written.
    return create_async_engine(f"sqlite+aiosqlite:///{db_path}")


async def _fetch_audit_events(db_path: Path) -> list[AuditEvent]:
    engine = _sqlite_engine(db_path)
    sessionmaker = get_sessionmaker(engine)
    async with sessionmaker() as session:
        result = await session.execute(select(AuditEvent).order_by(AuditEvent.id))
        events = list(result.scalars().all())
    await engine.dispose()
    return events


def test_clean_request_is_allowed_and_audited(tmp_path):
    db_path = tmp_path / "audit.db"
    provider = FakeProvider(response=FAKE_UPSTREAM_RESPONSE)
    app = create_app(provider=provider, engine=_sqlite_engine(db_path), run_migrations=True)

    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hi"}]},
            headers={"x-controlplane-tenant": "customer_support"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["choices"][0]["message"]["content"] == "Thanks for reaching out! How can I help you today?"
    assert body["controlplane"]["decision"] == "ALLOW"
    assert body["controlplane"]["tenant_id"] == "customer_support"
    assert provider.last_payload == {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "Hi"}],
    }

    events = asyncio.run(_fetch_audit_events(db_path))
    assert len(events) == 1
    assert events[0].decision == "ALLOW"
    assert events[0].tenant_id == "customer_support"
    assert verify_chain(events) is True


def test_unknown_tenant_is_rejected_without_calling_provider(tmp_path):
    db_path = tmp_path / "audit.db"
    provider = FakeProvider(response=FAKE_UPSTREAM_RESPONSE)
    app = create_app(provider=provider, engine=_sqlite_engine(db_path), run_migrations=True)

    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hi"}]},
            headers={"x-controlplane-tenant": "not_a_real_tenant"},
        )

    assert response.status_code == 400
    assert provider.last_payload is None


def test_provider_failure_is_surfaced_and_audited_with_error(tmp_path):
    db_path = tmp_path / "audit.db"
    provider = FakeProvider(error=ProviderError("upstream timed out"))
    app = create_app(provider=provider, engine=_sqlite_engine(db_path), run_migrations=True)

    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hi"}]},
            headers={"x-controlplane-tenant": "customer_support"},
        )

    assert response.status_code == 502

    events = asyncio.run(_fetch_audit_events(db_path))
    assert len(events) == 1
    assert events[0].decision == "ERROR"
    assert events[0].error == "upstream timed out"
    assert verify_chain(events) is True


def test_three_tenants_get_independent_policy_resolution(tmp_path):
    db_path = tmp_path / "audit.db"
    provider = FakeProvider(response=FAKE_UPSTREAM_RESPONSE)
    app = create_app(provider=provider, engine=_sqlite_engine(db_path), run_migrations=True)

    with TestClient(app) as client:
        health = client.get("/healthz").json()
        assert health["tenants"] == ["customer_support", "internal_copilot", "regulated_agent"]

        for tenant in health["tenants"]:
            response = client.post(
                "/v1/chat/completions",
                json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hi"}]},
                headers={"x-controlplane-tenant": tenant},
            )
            assert response.status_code == 200
            assert response.json()["controlplane"]["tenant_id"] == tenant
