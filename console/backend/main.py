"""ControlPlane console backend: a small, read-only FastAPI service over
the same audit ledger the gateway writes to (spec §26: "the dashboard
should eventually consume real system data rather than hard-coded demo
numbers" -- every number here comes from a live query, nothing is
hard-coded demo data).

Deliberately a separate process/app from the governance gateway: an
introspection surface has no business running in the same process as the
thing being introspected, and it only ever reads.

    uvicorn console.backend.main:app --reload --port 8001

Row kinds (ledger/models.py:AuditEvent.kind): "request" (one per gateway
call), "claim" (one per extracted claim), "tool_call" (one per gated
tool_calls entry) -- see ledger/models.py for why this is an explicit
column rather than inferred from which fields are set.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from bench.metrics.metrics import percentile
from ledger.db import get_engine, get_sessionmaker
from ledger.models import AuditEvent


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
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.get("/api/tenants")
    async def tenants():
        async with app.state.sessionmaker() as session:
            result = await session.execute(select(AuditEvent.tenant_id).distinct())
            return sorted(row[0] for row in result.all())

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
        }

    return app


app = create_app()
