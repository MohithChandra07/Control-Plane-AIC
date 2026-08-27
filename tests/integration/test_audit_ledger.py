import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from ledger.audit import AuditLedger, AuditRecord, verify_chain
from ledger.db import get_sessionmaker, init_models
from ledger.models import AuditEvent


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


async def test_chain_starts_from_genesis_and_links_events(sessionmaker):
    async with sessionmaker() as session:
        ledger = AuditLedger(session)
        first = await ledger.record(
            AuditRecord(
                request_id="req-1",
                tenant_id="customer_support",
                policy_name="customer_support",
                decision="ALLOW",
            )
        )
        second = await ledger.record(
            AuditRecord(
                request_id="req-2",
                tenant_id="customer_support",
                policy_name="customer_support",
                decision="BLOCK",
                claim_id="claim-1",
                verdict="UNVERIFIABLE",
                risk_labels={"hallucination": True},
                taint_status="tainted",
            )
        )

    assert first.prev_hash == "0" * 64
    assert second.prev_hash == first.hash
    assert first.hash != second.hash


async def test_verify_chain_detects_tampering(sessionmaker):
    async with sessionmaker() as session:
        ledger = AuditLedger(session)
        await ledger.record(
            AuditRecord(
                request_id="req-1",
                tenant_id="customer_support",
                policy_name="customer_support",
                decision="ALLOW",
            )
        )
        await ledger.record(
            AuditRecord(
                request_id="req-2",
                tenant_id="customer_support",
                policy_name="customer_support",
                decision="ALLOW",
            )
        )

    async with sessionmaker() as session:
        events = (await session.execute(select(AuditEvent).order_by(AuditEvent.id))).scalars().all()

    assert verify_chain(events) is True

    events[0].decision = "BLOCK"  # tamper with history in-place, not via record()
    assert verify_chain(events) is False


async def test_kind_defaults_to_request_and_round_trips(sessionmaker):
    async with sessionmaker() as session:
        ledger = AuditLedger(session)
        request_row = await ledger.record(
            AuditRecord(request_id="req-1", tenant_id="t", policy_name="t", decision="ALLOW")
        )
        claim_row = await ledger.record(
            AuditRecord(request_id="req-1", tenant_id="t", policy_name="t", decision="ALLOW", kind="claim")
        )
        tool_row = await ledger.record(
            AuditRecord(request_id="req-1", tenant_id="t", policy_name="t", decision="ALLOW", kind="tool_call")
        )

    assert request_row.kind == "request"
    assert claim_row.kind == "claim"
    assert tool_row.kind == "tool_call"

    async with sessionmaker() as session:
        events = (await session.execute(select(AuditEvent).order_by(AuditEvent.id))).scalars().all()
    assert verify_chain(events) is True
