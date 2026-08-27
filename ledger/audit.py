"""Append-only, hash-chained audit writer.

Each AuditEvent's `hash` commits to the previous event's `hash` plus its own
canonical field values (sha256). Recomputing the chain and comparing against
stored hashes makes any retroactive edit or deletion of a row evident —
that's the tamper-evidence property required by spec §16.

Concurrency note: this implementation reads the latest hash and inserts the
next row without a database-level lock, which is sufficient for this
prototype's demo/eval workloads (effectively one writer at a time). A
production deployment with concurrent writers would need SELECT ... FOR
UPDATE (or a single-writer queue) to make the chain race-free.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ledger.models import AuditEvent

GENESIS_HASH = "0" * 64


@dataclass
class AuditRecord:
    """Fields the caller supplies for one audit entry. Anything not
    yet known at this phase (claim_id, verdict, ...) defaults to None."""

    request_id: str
    tenant_id: str
    policy_name: str
    decision: str
    conversation_id: str | None = None
    turn_id: int | None = None
    claim_id: str | None = None
    verdict: str | None = None
    risk_labels: dict[str, Any] | None = None
    provenance: dict[str, Any] | None = None
    taint_status: str | None = None
    remediation: str | None = None
    action: dict[str, Any] | None = None
    latency_ms: float | None = None
    error: str | None = None
    _extra: dict[str, Any] = field(default_factory=dict, repr=False)


def _canonical_payload(record: AuditRecord, prev_hash: str) -> str:
    payload = {
        "prev_hash": prev_hash,
        "request_id": record.request_id,
        "tenant_id": record.tenant_id,
        "conversation_id": record.conversation_id,
        "turn_id": record.turn_id,
        "claim_id": record.claim_id,
        "verdict": record.verdict,
        "risk_labels": record.risk_labels,
        "provenance": record.provenance,
        "taint_status": record.taint_status,
        "remediation": record.remediation,
        "action": record.action,
        "policy_name": record.policy_name,
        "decision": record.decision,
        "latency_ms": record.latency_ms,
        "error": record.error,
    }
    return json.dumps(payload, sort_keys=True, default=str)


class AuditLedger:
    """Thin wrapper around one AsyncSession providing record-and-chain."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def _latest_hash(self) -> str:
        result = await self._session.execute(
            select(AuditEvent.hash).order_by(AuditEvent.id.desc()).limit(1)
        )
        row = result.scalar_one_or_none()
        return row or GENESIS_HASH

    async def record(self, record: AuditRecord) -> AuditEvent:
        prev_hash = await self._latest_hash()
        digest = hashlib.sha256(_canonical_payload(record, prev_hash).encode()).hexdigest()

        event = AuditEvent(
            request_id=record.request_id,
            tenant_id=record.tenant_id,
            conversation_id=record.conversation_id,
            turn_id=record.turn_id,
            claim_id=record.claim_id,
            verdict=record.verdict,
            risk_labels=record.risk_labels,
            provenance=record.provenance,
            taint_status=record.taint_status,
            remediation=record.remediation,
            action=record.action,
            policy_name=record.policy_name,
            decision=record.decision,
            latency_ms=record.latency_ms,
            error=record.error,
            prev_hash=prev_hash,
            hash=digest,
        )
        self._session.add(event)
        await self._session.commit()
        await self._session.refresh(event)
        return event


def verify_chain(events: list[AuditEvent]) -> bool:
    """Recompute the hash chain over `events` (ordered by id ascending) and
    return whether every stored hash matches. Used by tests and, later, the
    console's ledger-integrity view."""

    prev_hash = GENESIS_HASH
    for event in events:
        record = AuditRecord(
            request_id=event.request_id,
            tenant_id=event.tenant_id,
            policy_name=event.policy_name,
            decision=event.decision,
            conversation_id=event.conversation_id,
            turn_id=event.turn_id,
            claim_id=event.claim_id,
            verdict=event.verdict,
            risk_labels=event.risk_labels,
            provenance=event.provenance,
            taint_status=event.taint_status,
            remediation=event.remediation,
            action=event.action,
            latency_ms=event.latency_ms,
            error=event.error,
        )
        expected = hashlib.sha256(_canonical_payload(record, prev_hash).encode()).hexdigest()
        if expected != event.hash or event.prev_hash != prev_hash:
            return False
        prev_hash = event.hash
    return True
