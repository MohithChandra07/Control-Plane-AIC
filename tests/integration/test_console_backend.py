from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

from console.backend.main import create_app as create_console_app
from gateway.main import create_app as create_gateway_app
from gateway.providers.base import Provider


class FakeProvider(Provider):
    def __init__(self, content: str):
        self._content = content

    async def chat_completion(self, payload):
        return {
            "id": "chatcmpl-fake",
            "object": "chat.completion",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": self._content}, "finish_reason": "stop"}],
        }


def _seed_gateway_traffic(db_path: Path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    app = create_gateway_app(
        provider=FakeProvider("The customer's phone number is 9876543210 according to our records."),
        engine=engine,
        run_migrations=True,
    )
    with TestClient(app) as client:
        client.post(
            "/v1/chat/completions",
            json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
            headers={"x-controlplane-tenant": "customer_support"},
        )
        client.post(
            "/v1/chat/completions",
            json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
            headers={"x-controlplane-tenant": "internal_copilot"},
        )


def _console_client(db_path: Path) -> TestClient:
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    app = create_console_app(engine=engine)
    return TestClient(app)


def test_tenants_endpoint_lists_seen_tenants(tmp_path):
    db_path = tmp_path / "audit.db"
    _seed_gateway_traffic(db_path)
    with _console_client(db_path) as client:
        response = client.get("/api/tenants")
    assert response.status_code == 200
    assert set(response.json()) == {"customer_support", "internal_copilot"}


def test_summary_reports_real_decision_counts(tmp_path):
    db_path = tmp_path / "audit.db"
    _seed_gateway_traffic(db_path)
    with _console_client(db_path) as client:
        response = client.get("/api/summary")
    body = response.json()
    assert body["total_requests"] == 2
    assert sum(body["decision_counts"].values()) == 2
    assert body["latency_ms"]["p50"] is not None


def test_summary_filters_by_tenant(tmp_path):
    db_path = tmp_path / "audit.db"
    _seed_gateway_traffic(db_path)
    with _console_client(db_path) as client:
        response = client.get("/api/summary", params={"tenant": "customer_support"})
    assert response.json()["total_requests"] == 1


def test_events_list_returns_request_rows_only(tmp_path):
    db_path = tmp_path / "audit.db"
    _seed_gateway_traffic(db_path)
    with _console_client(db_path) as client:
        response = client.get("/api/events")
    events = response.json()
    assert len(events) == 2
    for e in events:
        assert "request_id" in e and "decision" in e


def test_event_detail_includes_claims(tmp_path):
    db_path = tmp_path / "audit.db"
    _seed_gateway_traffic(db_path)
    with _console_client(db_path) as client:
        request_id = client.get("/api/events").json()[0]["request_id"]
        detail = client.get(f"/api/events/{request_id}").json()

    assert detail["request"]["request_id"] == request_id
    assert len(detail["claims"]) == 1
    claim = detail["claims"][0]
    assert claim["verdict"] == "UNVERIFIABLE"
    assert "pii" in claim["risk_labels"]
    assert claim["risk_labels"]["pii"]["detected"] is True


def test_event_detail_404_for_unknown_request_id(tmp_path):
    db_path = tmp_path / "audit.db"
    _seed_gateway_traffic(db_path)
    with _console_client(db_path) as client:
        response = client.get("/api/events/does-not-exist")
    assert response.status_code == 404


def test_risk_appetite_defaults_to_half_when_unset(tmp_path):
    db_path = tmp_path / "audit.db"
    _seed_gateway_traffic(db_path)
    with _console_client(db_path) as client:
        response = client.get("/api/risk-appetite/customer_support")
    assert response.json() == {
        "tenant_id": "customer_support",
        "risk_appetite": 0.5,
        "updated_at": None,
        "updated_by": None,
    }


def test_setting_risk_appetite_persists_and_is_audited(tmp_path):
    db_path = tmp_path / "audit.db"
    _seed_gateway_traffic(db_path)
    with _console_client(db_path) as client:
        put_response = client.put(
            "/api/risk-appetite/customer_support",
            json={"risk_appetite": 0.9, "updated_by": "alice"},
        )
        assert put_response.status_code == 200

        get_response = client.get("/api/risk-appetite/customer_support")
        body = get_response.json()
        assert body["risk_appetite"] == 0.9
        assert body["updated_by"] == "alice"
        assert body["updated_at"] is not None

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import create_async_engine

    from ledger.audit import verify_chain
    from ledger.db import get_sessionmaker
    from ledger.models import AuditEvent

    async def _fetch():
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        sessionmaker = get_sessionmaker(engine)
        async with sessionmaker() as session:
            rows = (await session.execute(select(AuditEvent).order_by(AuditEvent.id))).scalars().all()
        await engine.dispose()
        return rows

    import asyncio

    events = asyncio.run(_fetch())
    change_rows = [e for e in events if e.kind == "risk_appetite_change"]
    assert len(change_rows) == 1
    assert change_rows[0].action == {"old_appetite": 0.5, "new_appetite": 0.9, "updated_by": "alice"}
    assert verify_chain(events) is True


def test_policies_endpoint_reflects_configs_yaml(tmp_path):
    db_path = tmp_path / "audit.db"
    _seed_gateway_traffic(db_path)
    with _console_client(db_path) as client:
        response = client.get("/api/policies")
    assert response.status_code == 200
    by_tenant = {p["tenant_id"]: p for p in response.json()}
    assert "regulated_agent" in by_tenant
    regulated = by_tenant["regulated_agent"]
    assert regulated["unverifiable_handling"] == "ESCALATE"
    assert regulated["tool_calls"]["consequential_sinks"] == [
        "money_movement",
        "database_write",
        "external_communication",
    ]


def test_risk_appetite_rejects_out_of_range_value(tmp_path):
    db_path = tmp_path / "audit.db"
    _seed_gateway_traffic(db_path)
    with _console_client(db_path) as client:
        response = client.put("/api/risk-appetite/customer_support", json={"risk_appetite": 1.5})
    assert response.status_code == 422


_DEMO_REQUEST_BODY = {
    "name": "Ada Lovelace",
    "work_email": "ada@example.com",
    "company": "Analytical Engines Inc",
    "role": "Head of AI",
    "ai_use_case": "Customer support automation",
    "primary_concern": "Governance",
}


def test_demo_request_rejects_missing_required_field(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_NOTIFICATION_EMAIL", "sales@example.com")
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    db_path = tmp_path / "audit.db"
    with _console_client(db_path) as client:
        response = client.post("/api/demo-request", json={**_DEMO_REQUEST_BODY, "company": ""})
    assert response.status_code == 422


def test_demo_request_rejects_invalid_email(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_NOTIFICATION_EMAIL", "sales@example.com")
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    db_path = tmp_path / "audit.db"
    with _console_client(db_path) as client:
        response = client.post("/api/demo-request", json={**_DEMO_REQUEST_BODY, "work_email": "not-an-email"})
    assert response.status_code == 422


def test_demo_request_503_when_notification_email_unconfigured(tmp_path, monkeypatch):
    monkeypatch.delenv("DEMO_NOTIFICATION_EMAIL", raising=False)
    db_path = tmp_path / "audit.db"
    with _console_client(db_path) as client:
        response = client.post("/api/demo-request", json=_DEMO_REQUEST_BODY)
    assert response.status_code == 503


def test_demo_request_sends_notification_and_confirmation_on_success(tmp_path, monkeypatch):
    import console.backend.main as backend_main

    monkeypatch.setenv("DEMO_NOTIFICATION_EMAIL", "sales@example.com")
    sent = []

    async def fake_send(*, to, subject, html_body, text_body):
        sent.append({"to": to, "subject": subject})

    monkeypatch.setattr(backend_main, "_send_resend_email", fake_send)

    db_path = tmp_path / "audit.db"
    with _console_client(db_path) as client:
        response = client.post("/api/demo-request", json=_DEMO_REQUEST_BODY)

    assert response.status_code == 201
    assert response.json() == {"status": "received"}
    assert [s["to"] for s in sent] == ["sales@example.com", "ada@example.com"]
    assert sent[0]["subject"] == "New ControlPlane Demo Request — Analytical Engines Inc"
    assert sent[1]["subject"] == "Your ControlPlane demo request"


def test_demo_request_fails_when_notification_email_fails(tmp_path, monkeypatch):
    import console.backend.main as backend_main

    monkeypatch.setenv("DEMO_NOTIFICATION_EMAIL", "sales@example.com")

    async def failing_send(*, to, subject, html_body, text_body):
        raise RuntimeError("Resend API returned 401: unauthorized")

    monkeypatch.setattr(backend_main, "_send_resend_email", failing_send)

    db_path = tmp_path / "audit.db"
    with _console_client(db_path) as client:
        response = client.post("/api/demo-request", json=_DEMO_REQUEST_BODY)

    assert response.status_code == 502
    # The real Resend error must never reach the client.
    assert "Resend" not in response.text
    assert "unauthorized" not in response.text


def test_demo_request_succeeds_even_if_visitor_confirmation_fails(tmp_path, monkeypatch):
    import console.backend.main as backend_main

    monkeypatch.setenv("DEMO_NOTIFICATION_EMAIL", "sales@example.com")
    calls = []

    async def mixed_send(*, to, subject, html_body, text_body):
        calls.append(to)
        if to != "sales@example.com":
            raise RuntimeError("Resend API returned 422: invalid recipient")

    monkeypatch.setattr(backend_main, "_send_resend_email", mixed_send)

    db_path = tmp_path / "audit.db"
    with _console_client(db_path) as client:
        response = client.post("/api/demo-request", json=_DEMO_REQUEST_BODY)

    # The lead is captured (notification succeeded) even though the
    # best-effort visitor confirmation failed.
    assert response.status_code == 201
    assert calls == ["sales@example.com", "ada@example.com"]
