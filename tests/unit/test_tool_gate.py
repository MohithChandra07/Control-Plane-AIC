import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from ledger.audit import AuditLedger, AuditRecord
from ledger.db import get_sessionmaker, init_models
from policy.loader import load_policy
from policy.models import Policy, Remediation, ToolCallPolicy
from policy.tool_gate import gate_tool_call
from policy.tools import ToolSpec

TOOL_SPECS = {
    "issue_refund": ToolSpec(sink="money_movement", tainted_args=["amount"]),
}


@pytest_asyncio.fixture
async def sessionmaker():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    await init_models(engine)
    yield get_sessionmaker(engine)
    await engine.dispose()


async def _seed_tainted_claim(sessionmaker, conversation_id: str, claim_text: str):
    async with sessionmaker() as session:
        await AuditLedger(session).record(
            AuditRecord(
                request_id="req-1",
                tenant_id="regulated_agent",
                policy_name="regulated_agent",
                decision="ESCALATE",
                conversation_id=conversation_id,
                claim_id="claim-1",
                claim_text=claim_text,
                verdict="UNVERIFIABLE",
            )
        )


async def test_tainted_argument_is_blocked_for_regulated_agent(sessionmaker):
    await _seed_tainted_claim(sessionmaker, "conv-1", "Customer is owed ₹48,000.")
    policy = load_policy("regulated_agent")
    assert policy.tool_calls.tainted_argument_action == Remediation.BLOCK

    async with sessionmaker() as session:
        decision = await gate_tool_call(
            session, "conv-1", "issue_refund", {"amount": 48000}, policy, TOOL_SPECS
        )
    assert decision.decision == Remediation.BLOCK
    assert "amount" in decision.tainted_args
    assert decision.sink == "money_movement"


async def test_untainted_argument_is_allowed(sessionmaker):
    policy = load_policy("regulated_agent")
    async with sessionmaker() as session:
        decision = await gate_tool_call(
            session, "conv-1", "issue_refund", {"amount": 100}, policy, TOOL_SPECS
        )
    assert decision.decision == Remediation.ALLOW
    assert decision.tainted_args == {}


async def test_tool_calls_disabled_always_allows(sessionmaker):
    await _seed_tainted_claim(sessionmaker, "conv-1", "Customer is owed ₹48,000.")
    policy = load_policy("customer_support")  # tool_calls.enabled = false
    assert policy.tool_calls.enabled is False

    async with sessionmaker() as session:
        decision = await gate_tool_call(
            session, "conv-1", "issue_refund", {"amount": 48000}, policy, TOOL_SPECS
        )
    assert decision.decision == Remediation.ALLOW


async def test_unknown_tool_is_allowed(sessionmaker):
    policy = load_policy("regulated_agent")
    async with sessionmaker() as session:
        decision = await gate_tool_call(
            session, "conv-1", "some_unclassified_tool", {"amount": 48000}, policy, TOOL_SPECS
        )
    assert decision.decision == Remediation.ALLOW
    assert decision.sink is None


async def test_sink_not_consequential_for_tenant_is_allowed_even_when_tainted(sessionmaker):
    """tool_calls.enabled=True, but this tenant only cares about
    database_write -- money_movement isn't gated for them, so a tainted
    refund amount still passes through ungated (a deliberate, visible
    policy choice, not a bug)."""
    await _seed_tainted_claim(sessionmaker, "conv-1", "Customer is owed ₹48,000.")
    policy = Policy(
        tenant_id="narrow_tenant",
        display_name="Narrow Tenant",
        latency_budget_ms=1000,
        tool_calls=ToolCallPolicy(
            enabled=True,
            consequential_sinks=["database_write"],
            tainted_argument_action=Remediation.BLOCK,
        ),
    )
    async with sessionmaker() as session:
        decision = await gate_tool_call(
            session, "conv-1", "issue_refund", {"amount": 48000}, policy, TOOL_SPECS
        )
    assert decision.decision == Remediation.ALLOW
