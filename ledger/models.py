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
    # Discriminates the three kinds of row one request can produce:
    # "request" (one per call, always), "claim" (one per extracted
    # claim), "tool_call" (one per gated tool_calls entry). Explicit
    # rather than inferred from which JSON fields happen to be set --
    # both a request row (model-routing info) and a tool_call row
    # (tool_name/sink/tainted_args) populate `action`, so that alone
    # can't tell them apart. console/backend/main.py relies on this.
    kind: Mapped[str] = mapped_column(String(16), default="request", index=True)

    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    turn_id: Mapped[int | None] = mapped_column(nullable=True)

    # Claim-level fields (populated from Phase 2 onward).
    claim_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # The claim's text, not just its metadata -- Phase 3's taint lookup
    # (ledger/taint.py) needs to match a later tool-call argument value
    # back to the claim text it came from.
    claim_text: Mapped[str | None] = mapped_column(Text, nullable=True)
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


class TenantSetting(Base):
    """Per-tenant console-controlled overrides (spec §20: risk appetite).

    Deliberately its own small mutable table, not an audit_events row --
    it's live *configuration* the gateway reads on every request, not a
    historical decision record. Every *change* to it is still audited
    (console/backend/main.py records an audit_events row with
    kind="risk_appetite_change" when this is written), so the audit
    ledger still has a complete, tamper-evident history of who changed
    what and when -- this table just holds the current value.
    """

    __tablename__ = "tenant_settings"

    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    risk_appetite: Mapped[float] = mapped_column(Float, default=0.5)
    updated_at: Mapped[dt.datetime] = mapped_column(
        default=lambda: dt.datetime.now(dt.UTC), onupdate=lambda: dt.datetime.now(dt.UTC)
    )
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
