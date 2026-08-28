"""Scene 8 (spec §15): the exact same request under three tenants.
Proves policy differentiation end-to-end through the real gateway --
Phase 2/3 already proved this at the policy-engine unit level
(tests/unit/test_policy_engine.py); this is the same claim, same
invariant, exercised as an actual HTTP round trip through all three real
tenant configs against one shared response."""

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

from gateway.main import create_app
from gateway.providers.base import Provider

# An unverifiable claim (no corpus backing), with just enough digits to
# clear every tenant's Tier 0 -> Tier 1 gate (customer_support=0.3,
# internal_copilot=0.5, regulated_agent=0.2) but not enough to read as
# PII -- isolates the tenant differentiation to unverifiable_handling,
# which genuinely differs per configs/*.yaml: customer_support=HEDGE,
# internal_copilot=ALLOW, regulated_agent=ESCALATE.
UNVERIFIABLE_CONTENT = "Your account standing is currently rated 92 out of 100 by our internal review team."


class FixedProvider(Provider):
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


def test_same_request_produces_different_decisions_per_tenant(tmp_path):
    db_path = tmp_path / "audit.db"
    app = create_app(provider=FixedProvider(UNVERIFIABLE_CONTENT), engine=_sqlite_engine(db_path), run_migrations=True)

    payload = {"model": "gpt-4o", "messages": [{"role": "user", "content": "How am I doing?"}]}
    results = {}

    with TestClient(app) as client:
        for tenant in ("customer_support", "internal_copilot", "regulated_agent"):
            response = client.post(
                "/v1/chat/completions", json=payload, headers={"x-controlplane-tenant": tenant}
            )
            assert response.status_code == 200
            body = response.json()
            results[tenant] = {
                "decision": body["controlplane"]["decision"],
                "content": body["choices"][0]["message"]["content"],
                "remediation": body["controlplane"]["claims"][0]["remediation"] if body["controlplane"]["claims"] else None,
            }

    # Same input, same claim verdict (UNVERIFIABLE) everywhere -- but three
    # genuinely different outcomes, because policy differs, not detection.
    assert results["customer_support"]["remediation"] == "HEDGE"
    assert results["internal_copilot"]["remediation"] == "ALLOW"
    assert results["regulated_agent"]["remediation"] == "ESCALATE"

    assert results["customer_support"]["decision"] == "MODIFY"
    assert results["internal_copilot"]["decision"] == "ALLOW"
    assert results["regulated_agent"]["decision"] == "ESCALATE"

    # internal_copilot is the only one whose response text is untouched --
    # ALLOW means the claim passed through verbatim, no hedging language added.
    assert results["internal_copilot"]["content"] == UNVERIFIABLE_CONTENT
    assert results["customer_support"]["content"] != UNVERIFIABLE_CONTENT  # hedge prefix was added
    assert len({r["decision"] for r in results.values()}) == 3  # all three genuinely differ
