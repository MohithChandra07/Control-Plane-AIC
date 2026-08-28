"""Scenes 5-7 (spec §15), Phase 3: cost circuit breaker, cheap-model
reroute, and the critical tainted-refund tool-call block -- all exercised
through the real gateway (real GovernanceEngine, real tool sink catalog,
real taint lookup against the audit ledger) with a scripted fake provider
standing in for the upstream LLM.
"""

import asyncio
import json
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


def _completion(content: str | None = None, tool_calls: list[dict] | None = None) -> dict:
    message: dict[str, Any] = {"role": "assistant", "content": content}
    if tool_calls is not None:
        message["tool_calls"] = tool_calls
    return {
        "id": "chatcmpl-fake",
        "object": "chat.completion",
        "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
    }


class FixedProvider(Provider):
    """Same response every call, regardless of requested model."""

    def __init__(self, response: dict):
        self._response = response
        self.call_count = 0

    async def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.call_count += 1
        return self._response


class ByModelProvider(Provider):
    """Different response depending on the "model" field of the payload."""

    def __init__(self, responses_by_model: dict[str, dict]):
        self._responses = responses_by_model
        self.call_count = 0
        self.models_called: list[str | None] = []

    async def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.call_count += 1
        model = payload.get("model")
        self.models_called.append(model)
        return self._responses[model]


class SequentialProvider(Provider):
    """Returns responses in order, one per call -- for scripting a
    multi-turn conversation where the client resends full history."""

    def __init__(self, responses: list[dict]):
        self._responses = responses
        self.call_count = 0

    async def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._responses[self.call_count]
        self.call_count += 1
        return response


def _post(client: TestClient, tenant: str, content: str = "Hi", conversation_id: str | None = None, model: str | None = None):
    payload: dict[str, Any] = {"model": model or "gpt-4o", "messages": [{"role": "user", "content": content}]}
    if conversation_id:
        payload["controlplane"] = {"conversation_id": conversation_id}
    return client.post("/v1/chat/completions", json=payload, headers={"x-controlplane-tenant": tenant})


# --- Scene 5: retry storm / token spike -> cost circuit breaker ---


def test_scene5_retry_storm_trips_cost_breaker(tmp_path):
    db_path = tmp_path / "audit.db"
    provider = FixedProvider(_completion("Thanks for reaching out! How can I help you today?"))
    app = create_app(provider=provider, engine=_sqlite_engine(db_path), run_migrations=True)

    # customer_support: max_requests_per_window = 30 (configs/customer_support.yaml)
    with TestClient(app) as client:
        for _ in range(30):
            response = _post(client, "customer_support")
            assert response.status_code == 200

        tripped = _post(client, "customer_support")
        assert tripped.status_code == 429

    assert provider.call_count == 30  # the 31st request never reached the provider

    events = asyncio.run(_fetch_audit_events(db_path))
    tripped_row = events[-1]
    assert tripped_row.decision == "BLOCK"
    assert "cost circuit breaker" in tripped_row.error
    assert verify_chain(events) is True


# --- Scene 6: cheap-model reroute validated by checker ---


def test_scene6_flagged_cheap_response_reroutes_to_escalation_model(tmp_path):
    db_path = tmp_path / "audit.db"
    cheap_response = _completion("Your refund processing will definitely take 2 hours.")  # contradicts corpus
    escalation_response = _completion("Refund processing takes 5 to 7 business days after approval.")  # grounded
    provider = ByModelProvider({"gpt-4o-mini": cheap_response, "gpt-4o": escalation_response})
    app = create_app(provider=provider, engine=_sqlite_engine(db_path), run_migrations=True)

    with TestClient(app) as client:
        response = _post(client, "customer_support")  # model_routing.enabled = true

    assert response.status_code == 200
    body = response.json()
    assert provider.call_count == 2
    assert provider.models_called == ["gpt-4o-mini", "gpt-4o"]
    assert body["controlplane"]["rerouted"] is True
    assert body["controlplane"]["model_used"] == "gpt-4o"
    assert body["controlplane"]["decision"] != "ESCALATE"  # the escalation model's answer passed the checker
    assert "5 to 7 business days" in body["choices"][0]["message"]["content"]
    assert "2 hours" not in body["choices"][0]["message"]["content"]


def test_scene6_no_reroute_when_cheap_model_passes(tmp_path):
    db_path = tmp_path / "audit.db"
    cheap_response = _completion("Thanks for reaching out! How can I help you today?")
    provider = ByModelProvider({"gpt-4o-mini": cheap_response})
    app = create_app(provider=provider, engine=_sqlite_engine(db_path), run_migrations=True)

    with TestClient(app) as client:
        response = _post(client, "customer_support")

    assert response.status_code == 200
    assert provider.call_count == 1  # never had to call the escalation model
    assert response.json()["controlplane"]["rerouted"] is False


# --- Scene 7 (CRITICAL): agent proposes a refund using a tainted value ---


def test_scene7_tainted_refund_amount_blocks_tool_call(tmp_path):
    db_path = tmp_path / "audit.db"
    conversation_id = "conv-scene7"

    turn1_response = _completion("Customer is owed ₹48,000 according to their message, though this is unconfirmed.")
    turn2_response = _completion(
        content=None,
        tool_calls=[
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "issue_refund", "arguments": json.dumps({"amount": 48000})},
            }
        ],
    )
    provider = SequentialProvider([turn1_response, turn2_response])
    # regulated_agent: model_routing disabled, tool_calls enabled, money_movement
    # consequential, tainted_argument_action = BLOCK.
    app = create_app(provider=provider, engine=_sqlite_engine(db_path), run_migrations=True)

    with TestClient(app) as client:
        turn1 = _post(
            client, "regulated_agent", content="What does the customer say they're owed?", conversation_id=conversation_id
        )
        assert turn1.status_code == 200
        assert turn1.json()["controlplane"]["decision"] == "ESCALATE"

        turn2 = _post(
            client,
            "regulated_agent",
            content="Second message so this counts as a new turn.",
            conversation_id=conversation_id,
        )

    assert turn2.status_code == 200
    body = turn2.json()
    assert body["controlplane"]["decision"] == "BLOCK"
    assert len(body["controlplane"]["tool_calls"]) == 1
    tool_decision = body["controlplane"]["tool_calls"][0]
    assert tool_decision["tool_name"] == "issue_refund"
    assert tool_decision["decision"] == "BLOCK"
    assert tool_decision["tainted_args"] == ["amount"]

    # The blocked call must never reach the application as something to execute.
    assert "tool_calls" not in body["choices"][0]["message"]

    events = asyncio.run(_fetch_audit_events(db_path))
    assert verify_chain(events) is True
    tool_rows = [e for e in events if e.action and e.action.get("tool_name") == "issue_refund"]
    assert len(tool_rows) == 1
    assert tool_rows[0].remediation == "BLOCK"
    tainted_claim_id = tool_rows[0].action["tainted_args"]["amount"]

    turn1_claim_row = next(e for e in events if e.claim_id == tainted_claim_id)
    assert turn1_claim_row.turn_id == 1
    assert turn1_claim_row.verdict == "UNVERIFIABLE"
    assert turn1_claim_row.taint_status == "tainted"


def test_scene7_untainted_refund_amount_is_allowed(tmp_path):
    """Same tool, same tenant -- but nothing tainted the amount, so it goes
    through. Proves the gate isn't just blocking issue_refund outright."""
    db_path = tmp_path / "audit.db"
    conversation_id = "conv-scene7-clean"

    turn1_response = _completion("Thanks for reaching out! How can I help you today?")
    turn2_response = _completion(
        content=None,
        tool_calls=[
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "issue_refund", "arguments": json.dumps({"amount": 250})},
            }
        ],
    )
    provider = SequentialProvider([turn1_response, turn2_response])
    app = create_app(provider=provider, engine=_sqlite_engine(db_path), run_migrations=True)

    with TestClient(app) as client:
        _post(client, "regulated_agent", content="Hi there", conversation_id=conversation_id)
        turn2 = _post(client, "regulated_agent", content="Please process it", conversation_id=conversation_id)

    body = turn2.json()
    assert body["controlplane"]["tool_calls"][0]["decision"] == "ALLOW"
    assert body["controlplane"]["tool_calls"][0]["tainted_args"] == []
    assert "tool_calls" in body["choices"][0]["message"]
