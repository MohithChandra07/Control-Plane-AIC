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
