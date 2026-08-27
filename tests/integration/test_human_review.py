"""Scene 9: human reviewer override. Proves the feedback loop end to end
-- a human can review a past decision, the review is audited, a real
human-agreement rate is computed from it (closing the gap Phase 4 left
undone for lack of any human-labeled data), and a recalibration
suggestion appears once disagreement is high enough."""

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
            "choices": [
                {"index": 0, "message": {"role": "assistant", "content": self._content}, "finish_reason": "stop"}
            ],
        }


def _seed_escalations(db_path: Path, count: int) -> list[str]:
    """Seeds `count` requests that each produce an ESCALATE decision
    (a CONTRADICTED claim under customer_support), returning their
    request_ids."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    app = create_gateway_app(
        provider=FakeProvider("Refund processing takes 2 business days after approval."),
        engine=engine,
        run_migrations=True,
    )
    request_ids = []
    with TestClient(app) as client:
        for _ in range(count):
            response = client.post(
                "/v1/chat/completions",
                json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
                headers={"x-controlplane-tenant": "customer_support"},
            )
            request_ids.append(response.json()["controlplane"]["request_id"])
    return request_ids


def _console_client(db_path: Path) -> TestClient:
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    return TestClient(create_console_app(engine=engine))


def test_submitting_a_review_is_recorded_and_visible_on_the_request(tmp_path):
    db_path = tmp_path / "audit.db"
    [request_id] = _seed_escalations(db_path, 1)

    with _console_client(db_path) as client:
        response = client.post(
            "/api/reviews",
            json={"request_id": request_id, "reviewer": "alice", "agree": False, "notes": "too aggressive"},
        )
        assert response.status_code == 200

        detail = client.get(f"/api/events/{request_id}").json()
    assert len(detail["reviews"]) == 1
    assert detail["reviews"][0]["reviewer"] == "alice"
    assert detail["reviews"][0]["agree"] is False
    assert detail["reviews"][0]["reviewed_decision"] == "ESCALATE"


def test_review_of_unknown_request_is_404(tmp_path):
    db_path = tmp_path / "audit.db"
    _seed_escalations(db_path, 1)
    with _console_client(db_path) as client:
        response = client.post(
            "/api/reviews", json={"request_id": "does-not-exist", "reviewer": "alice", "agree": True}
        )
    assert response.status_code == 404


def test_claim_level_review_uses_the_claims_own_remediation(tmp_path):
    db_path = tmp_path / "audit.db"
    [request_id] = _seed_escalations(db_path, 1)

    with _console_client(db_path) as client:
        detail = client.get(f"/api/events/{request_id}").json()
        claim_id = detail["claims"][0]["claim_id"]

        client.post(
            "/api/reviews",
            json={"request_id": request_id, "claim_id": claim_id, "reviewer": "bob", "agree": True},
        )
        detail = client.get(f"/api/events/{request_id}").json()

    assert len(detail["reviews"]) == 1
    assert detail["reviews"][0]["reviewed_claim_id"] == claim_id


def test_human_agreement_rate_is_computed_from_real_reviews(tmp_path):
    db_path = tmp_path / "audit.db"
    request_ids = _seed_escalations(db_path, 4)

    with _console_client(db_path) as client:
        for i, rid in enumerate(request_ids):
            client.post(
                "/api/reviews",
                json={"request_id": rid, "reviewer": "alice", "agree": i < 3},  # 3 agree, 1 disagree
            )
        result = client.get("/api/human-agreement/customer_support").json()

    assert result["reviewed_count"] == 4
    assert result["agreement_rate"] == 0.75


def test_human_agreement_is_none_with_no_reviews(tmp_path):
    db_path = tmp_path / "audit.db"
    _seed_escalations(db_path, 1)
    with _console_client(db_path) as client:
        result = client.get("/api/human-agreement/customer_support").json()
    assert result == {"tenant_id": "customer_support", "reviewed_count": 0, "agreement_rate": None}


def test_recalibration_suggests_relaxing_after_high_disagreement(tmp_path):
    db_path = tmp_path / "audit.db"
    request_ids = _seed_escalations(db_path, 5)

    with _console_client(db_path) as client:
        for rid in request_ids:
            client.post("/api/reviews", json={"request_id": rid, "reviewer": "alice", "agree": False})
        result = client.get("/api/recalibration/customer_support").json()

    assert result["suggestion"] is not None
    assert result["suggestion"]["reviewed_count"] == 5
    assert result["suggestion"]["suggested_appetite_delta"] < 0


def test_no_recalibration_suggestion_when_reviewers_agree(tmp_path):
    db_path = tmp_path / "audit.db"
    request_ids = _seed_escalations(db_path, 5)

    with _console_client(db_path) as client:
        for rid in request_ids:
            client.post("/api/reviews", json={"request_id": rid, "reviewer": "alice", "agree": True})
        result = client.get("/api/recalibration/customer_support").json()

    assert result["suggestion"] is None


def test_list_reviews_returns_recent_reviews(tmp_path):
    db_path = tmp_path / "audit.db"
    [request_id] = _seed_escalations(db_path, 1)

    with _console_client(db_path) as client:
        client.post("/api/reviews", json={"request_id": request_id, "reviewer": "alice", "agree": True})
        reviews = client.get("/api/reviews", params={"tenant": "customer_support"}).json()

    assert len(reviews) == 1
    assert reviews[0]["reviewer"] == "alice"
