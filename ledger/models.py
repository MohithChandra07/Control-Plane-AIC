"""Audit ledger schema.

One row per governance decision ControlPlane makes. In Phase 1 that's one
row per gateway request (decision=ALLOW, no claims yet). From Phase 2
onward, claim-level fields (verdict, risk_labels, provenance, taint_status,
remediation) and tool-call fields (action) are populated per the spec.

The table is intentionally append-only: rows are never updated or deleted
by application code (see ledger/audit.py), and each row's `hash` commits to
the previous row's hash so tampering with history is detectable.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, Float, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    request_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        default=lambda: dt.datetime.now(dt.UTC)
    )

    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    turn_id: Mapped[int | None] = mapped_column(nullable=True)

    # Claim-level fields (populated from Phase 2 onward).
    claim_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verdict: Mapped[str | None] = mapped_column(String(32), nullable=True)
    risk_labels: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    provenance: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    taint_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    remediation: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Tool-call / action-gating fields (populated from Phase 3 onward).
    action: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    policy_name: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(String(32))
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
