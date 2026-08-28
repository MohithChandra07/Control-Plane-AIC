"""ControlPlane console backend: a small FastAPI service over the same
audit ledger the gateway writes to (spec §26: "the dashboard should
eventually consume real system data rather than hard-coded demo numbers"
-- every number here comes from a live query, nothing is hard-coded demo
data).

Deliberately a separate process/app from the governance gateway: an
introspection surface has no business running in the same process as the
thing being introspected.

Mostly read-only, with two narrowly-scoped admin write endpoints Phase 5
adds: risk appetite (spec §20) and human review (spec Scene 9). Both are
policy-affecting actions, so both are audited through the same
hash-chained ledger the gateway itself uses (CLAUDE.md rule #5: no second,
unaudited way to make a governance-adjacent decision) -- writing a
TenantSetting row always also writes an audit_events row recording who
changed what, when, from what, to what.

    uvicorn console.backend.main:app --reload --port 8001

Row kinds (ledger/models.py:AuditEvent.kind): "request" (one per gateway
call), "claim" (one per extracted claim), "tool_call" (one per gated
tool_calls entry), "risk_appetite_change" / "human_review" (Phase 5's admin
actions) -- see ledger/models.py for why this is an explicit column
rather than inferred from which fields are set.
"""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from bench.metrics.metrics import percentile
from ledger.audit import AuditLedger, AuditRecord
from ledger.db import get_engine, get_sessionmaker
from ledger.models import AuditEvent, TenantSetting
from policy.recalibration import suggest_recalibration


class RiskAppetiteUpdate(BaseModel):
    risk_appetite: float = Field(ge=0.0, le=1.0)
    updated_by: str | None = None


class ReviewSubmission(BaseModel):
    request_id: str
    claim_id: str | None = None
    reviewer: str
    agree: bool
    notes: str | None = None


def create_app(*, engine: AsyncEngine | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.engine = engine or get_engine()
        app.state.sessionmaker = get_sessionmaker(app.state.engine)
        yield
        await app.state.engine.dispose()

    app = FastAPI(title="ControlPlane Console API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.environ.get("CONSOLE_CORS_ORIGINS", "http://localhost:5173").split(","),
        allow_methods=["GET", "PUT", "POST"],
        allow_headers=["*"],
    )

    @app.get("/api/tenants")
    async def tenants():
        async with app.state.sessionmaker() as session:
            result = await session.execute(select(AuditEvent.tenant_id).distinct())
            return sorted(row[0] for row in result.all())

    @app.get("/api/risk-appetite/{tenant}")
    async def get_risk_appetite(tenant: str):
        async with app.state.sessionmaker() as session:
            setting = await session.get(TenantSetting, tenant)
        if setting is None:
            return {"tenant_id": tenant, "risk_appetite": 0.5, "updated_at": None, "updated_by": None}
        return {
            "tenant_id": setting.tenant_id,
            "risk_appetite": setting.risk_appetite,
            "updated_at": setting.updated_at,
            "updated_by": setting.updated_by,
        }

    @app.put("/api/risk-appetite/{tenant}")
    async def set_risk_appetite(tenant: str, body: RiskAppetiteUpdate):
        async with app.state.sessionmaker() as session:
            setting = await session.get(TenantSetting, tenant)
            old_appetite = setting.risk_appetite if setting else 0.5
            if setting is None:
                setting = TenantSetting(tenant_id=tenant)
                session.add(setting)
            setting.risk_appetite = body.risk_appetite
            setting.updated_by = body.updated_by

            # Changing risk appetite is a policy-affecting action -- audit
            # it through the same hash-chained ledger the gateway uses,
            # not a side channel (CLAUDE.md rule #5).
            await AuditLedger(session).record(
                AuditRecord(
                    request_id=f"admin-{uuid.uuid4()}",
                    tenant_id=tenant,
                    policy_name=tenant,
                    decision="ADMIN_ACTION",
                    kind="risk_appetite_change",
                    action={
                        "old_appetite": old_appetite,
                        "new_appetite": body.risk_appetite,
                        "updated_by": body.updated_by,
                    },
                )
            )
            # AuditLedger.record() above already commits the session,
            # flushing this TenantSetting write in the same transaction.

        return {"tenant_id": tenant, "risk_appetite": body.risk_appetite, "updated_by": body.updated_by}

    @app.post("/api/reviews")
    async def submit_review(body: ReviewSubmission):
        """Records a human reviewer's judgment on a past decision (Scene
        9). Looks up what was actually decided rather than trusting a
        client-asserted decision, so the review -- and anything
        suggest_recalibration() later derives from it -- is grounded in
        the real audit trail, not whatever the caller claims happened."""
        async with app.state.sessionmaker() as session:
            stmt = select(AuditEvent).where(AuditEvent.request_id == body.request_id)
            stmt = stmt.where(
                AuditEvent.claim_id == body.claim_id if body.claim_id else AuditEvent.kind == "request"
            )
            target = (await session.execute(stmt)).scalars().first()
            if target is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"no matching event for request_id={body.request_id!r} claim_id={body.claim_id!r}",
                )

            reviewed_decision = target.remediation if body.claim_id else target.decision

            await AuditLedger(session).record(
                AuditRecord(
                    request_id=f"review-{uuid.uuid4()}",
                    tenant_id=target.tenant_id,
                    policy_name=target.tenant_id,
                    decision="ADMIN_ACTION",
                    kind="human_review",
                    action={
                        "reviewed_request_id": body.request_id,
                        "reviewed_claim_id": body.claim_id,
                        "reviewed_decision": reviewed_decision,
                        "reviewer": body.reviewer,
                        "agree": body.agree,
                        "notes": body.notes,
                    },
                )
            )

        return {"status": "recorded"}

    @app.get("/api/reviews")
    async def list_reviews(tenant: str | None = None, limit: int = Query(50, ge=1, le=500)):
        async with app.state.sessionmaker() as session:
            stmt = select(AuditEvent).where(AuditEvent.kind == "human_review")
            if tenant:
                stmt = stmt.where(AuditEvent.tenant_id == tenant)
            stmt = stmt.order_by(AuditEvent.id.desc()).limit(limit)
            rows = (await session.execute(stmt)).scalars().all()
        return [{"tenant_id": r.tenant_id, "created_at": r.created_at, **(r.action or {})} for r in rows]

    @app.get("/api/human-agreement/{tenant}")
    async def human_agreement(tenant: str):
        async with app.state.sessionmaker() as session:
            stmt = select(AuditEvent).where(AuditEvent.kind == "human_review", AuditEvent.tenant_id == tenant)
            rows = (await session.execute(stmt)).scalars().all()
        if not rows:
            return {"tenant_id": tenant, "reviewed_count": 0, "agreement_rate": None}
        agree_count = sum(1 for r in rows if r.action and r.action.get("agree"))
        return {"tenant_id": tenant, "reviewed_count": len(rows), "agreement_rate": agree_count / len(rows)}

    @app.get("/api/recalibration/{tenant}")
    async def recalibration(tenant: str):
        async with app.state.sessionmaker() as session:
            stmt = select(AuditEvent).where(AuditEvent.kind == "human_review", AuditEvent.tenant_id == tenant)
            rows = (await session.execute(stmt)).scalars().all()

        reviews = [
            {"decision": r.action.get("reviewed_decision"), "agree": r.action.get("agree")}
            for r in rows
            if r.action
        ]
        suggestion = suggest_recalibration(tenant, reviews)
        if suggestion is None:
            return {"tenant_id": tenant, "suggestion": None}
        return {
            "tenant_id": tenant,
            "suggestion": {
                "reviewed_count": suggestion.reviewed_count,
                "disagreement_rate": suggestion.disagreement_rate,
                "suggested_appetite_delta": suggestion.suggested_appetite_delta,
                "message": suggestion.message,
            },
        }

    @app.get("/api/summary")
    async def summary(tenant: str | None = None):
        async with app.state.sessionmaker() as session:
            stmt = select(AuditEvent).where(AuditEvent.kind == "request")
            if tenant:
                stmt = stmt.where(AuditEvent.tenant_id == tenant)
            rows = (await session.execute(stmt)).scalars().all()

        decision_counts: dict[str, int] = {}
        latencies: list[float] = []
        for row in rows:
            decision_counts[row.decision] = decision_counts.get(row.decision, 0) + 1
            if row.latency_ms is not None:
                latencies.append(row.latency_ms)

        return {
            "total_requests": len(rows),
            "decision_counts": decision_counts,
            "escalation_rate": (decision_counts.get("ESCALATE", 0) / len(rows)) if rows else None,
            "latency_ms": {
                "p50": percentile(latencies, 50),
                "p95": percentile(latencies, 95),
            },
        }

    @app.get("/api/events")
    async def events(
        tenant: str | None = None,
        decision: str | None = None,
        limit: int = Query(50, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ):
        async with app.state.sessionmaker() as session:
            stmt = select(AuditEvent).where(AuditEvent.kind == "request")
            if tenant:
                stmt = stmt.where(AuditEvent.tenant_id == tenant)
            if decision:
                stmt = stmt.where(AuditEvent.decision == decision)
            stmt = stmt.order_by(AuditEvent.id.desc()).offset(offset).limit(limit)
            rows = (await session.execute(stmt)).scalars().all()

        return [
            {
                "request_id": r.request_id,
                "tenant_id": r.tenant_id,
                "conversation_id": r.conversation_id,
                "turn_id": r.turn_id,
                "decision": r.decision,
                "latency_ms": r.latency_ms,
                "error": r.error,
                "created_at": r.created_at,
            }
            for r in rows
        ]

    @app.get("/api/events/{request_id}")
    async def event_detail(request_id: str):
        async with app.state.sessionmaker() as session:
            stmt = select(AuditEvent).where(AuditEvent.request_id == request_id).order_by(AuditEvent.id)
            rows = (await session.execute(stmt)).scalars().all()

        if not rows:
            raise HTTPException(status_code=404, detail=f"no events for request_id '{request_id}'")

        request_row = next((r for r in rows if r.kind == "request"), rows[0])
        claims = [r for r in rows if r.kind == "claim"]
        tool_calls = [r for r in rows if r.kind == "tool_call"]

        # Review rows carry their own request_id (review-<uuid>), not this
        # request's -- the link lives in action.reviewed_request_id, so
        # this can't be a plain WHERE request_id=... query. Reviews are
        # low-volume, so filtering in Python over this tenant's reviews is
        # fine for this prototype's scale.
        async with app.state.sessionmaker() as session:
            review_stmt = select(AuditEvent).where(
                AuditEvent.kind == "human_review", AuditEvent.tenant_id == request_row.tenant_id
            )
            review_rows = (await session.execute(review_stmt)).scalars().all()
        reviews = [
            {"created_at": r.created_at, **r.action}
            for r in review_rows
            if r.action and r.action.get("reviewed_request_id") == request_id
        ]

        return {
            "request": {
                "request_id": request_row.request_id,
                "tenant_id": request_row.tenant_id,
                "conversation_id": request_row.conversation_id,
                "turn_id": request_row.turn_id,
                "decision": request_row.decision,
                "latency_ms": request_row.latency_ms,
                "error": request_row.error,
                "action": request_row.action,
                "created_at": request_row.created_at,
            },
            "claims": [
                {
                    "claim_id": c.claim_id,
                    "claim_text": c.claim_text,
                    "verdict": c.verdict,
                    "risk_labels": c.risk_labels,
                    "provenance": c.provenance,
                    "taint_status": c.taint_status,
                    "remediation": c.remediation,
                }
                for c in claims
            ],
            "tool_calls": [
                {
                    "remediation": t.remediation,
                    "action": t.action,
                }
                for t in tool_calls
            ],
            "reviews": reviews,
        }

    return app


app = create_app()
