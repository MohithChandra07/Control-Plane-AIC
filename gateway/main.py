"""ControlPlane gateway entrypoint.

    uvicorn gateway.main:app --reload

Loads all tenant policies from configs/, sets up the Postgres-backed audit
ledger, and constructs the upstream provider from environment variables
(see .env.example). create_app() takes explicit overrides so tests can
inject a fake provider and an isolated (sqlite) engine instead of hitting a
real database/LLM — see tests/integration/test_gateway_roundtrip.py.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from detectors.hallucination.claim_verifier import ClaimVerifier
from detectors.hallucination.corpus import load_corpus
from gateway.middleware.cost_breaker import CostBreaker
from gateway.providers.base import Provider
from gateway.providers.openai_compatible import OpenAICompatibleProvider
from gateway.routes.chat import router as chat_router
from ledger.db import get_engine, get_sessionmaker, init_models
from policy.engine import GovernanceEngine
from policy.loader import load_all_policies
from policy.tools import load_tool_specs

load_dotenv()


def create_app(
    *,
    provider: Provider | None = None,
    engine: AsyncEngine | None = None,
    run_migrations: bool = False,
    governance_engine: GovernanceEngine | None = None,
    cost_breaker: CostBreaker | None = None,
) -> FastAPI:
    """Build the FastAPI app.

    `provider`/`engine`/`governance_engine`/`cost_breaker` override the
    defaults (real upstream provider, Postgres from DATABASE_URL, a
    ClaimVerifier built from the real data/corpus/ docs, a fresh
    per-process CostBreaker). `run_migrations=True` creates tables on the
    given engine at startup — production applies ledger/schema.sql out of
    band instead, so this is for tests/local dev only.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.policies = load_all_policies()
        app.state.default_tenant = os.environ.get("DEFAULT_TENANT", "customer_support")
        app.state.tool_specs = load_tool_specs()

        app.state.engine = engine or get_engine()
        app.state.sessionmaker = get_sessionmaker(app.state.engine)

        if run_migrations:
            await init_models(app.state.engine)

        app.state.provider = provider or OpenAICompatibleProvider(
            base_url=os.environ.get("UPSTREAM_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.environ.get("UPSTREAM_API_KEY", ""),
        )

        app.state.governance_engine = governance_engine or GovernanceEngine(
            ClaimVerifier(load_corpus())
        )
        app.state.cost_breaker = cost_breaker or CostBreaker()

        yield

        await app.state.engine.dispose()

    app = FastAPI(title="ControlPlane Gateway", lifespan=lifespan)
    app.include_router(chat_router)

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok", "tenants": sorted(app.state.policies.keys())}

    return app


app = create_app()
