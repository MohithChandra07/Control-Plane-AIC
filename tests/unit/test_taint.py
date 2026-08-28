import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from ledger.audit import AuditLedger, AuditRecord
from ledger.db import get_sessionmaker, init_models
from ledger.taint import find_taint


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


async def _seed_tainted_claim(sessionmaker, conversation_id: str, claim_text: str, verdict: str = "UNVERIFIABLE"):
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
                verdict=verdict,
            )
        )


async def test_finds_tainted_value_across_currency_formatting(sessionmaker):
    await _seed_tainted_claim(sessionmaker, "conv-1", "Customer is owed ₹48,000.")
    async with sessionmaker() as session:
        match = await find_taint(session, "conv-1", 48000)
    assert match is not None
    assert match.claim_id == "claim-1"
    assert match.verdict == "UNVERIFIABLE"


async def test_no_match_for_untainted_value(sessionmaker):
    await _seed_tainted_claim(sessionmaker, "conv-1", "Customer is owed ₹48,000.")
    async with sessionmaker() as session:
        match = await find_taint(session, "conv-1", 999)
    assert match is None


async def test_supported_claims_never_taint(sessionmaker):
    await _seed_tainted_claim(sessionmaker, "conv-1", "Refunds are available within 30 days.", verdict="SUPPORTED")
    async with sessionmaker() as session:
        match = await find_taint(session, "conv-1", 30)
    assert match is None


async def test_scoped_to_conversation(sessionmaker):
    await _seed_tainted_claim(sessionmaker, "conv-1", "Customer is owed 48000.")
    async with sessionmaker() as session:
        match = await find_taint(session, "conv-2", 48000)
    assert match is None


async def test_no_conversation_id_never_matches(sessionmaker):
    await _seed_tainted_claim(sessionmaker, "conv-1", "Customer is owed 48000.")
    async with sessionmaker() as session:
        match = await find_taint(session, None, 48000)
    assert match is None


async def test_non_numeric_value_returns_none(sessionmaker):
    await _seed_tainted_claim(sessionmaker, "conv-1", "Customer is owed 48000.")
    async with sessionmaker() as session:
        match = await find_taint(session, "conv-1", "not-a-number")
    assert match is None
