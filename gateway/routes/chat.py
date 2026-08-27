"""OpenAI-compatible /v1/chat/completions endpoint.

Phase 1 scope: resolve the tenant's policy, forward the request to the
upstream provider, and record an audit event for the decision. There is no
claim extraction, verification, or remediation yet (Phase 2) — every
successful call is currently decided ALLOW. That decision is still recorded
per-request through the same audit ledger later phases will extend, so the
"a real client can talk through ControlPlane and a decision is recorded"
definition of done (spec §23 Phase 1) holds end-to-end.
"""

from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, HTTPException, Request

from gateway.providers.base import ProviderError
from ledger.audit import AuditLedger, AuditRecord
from policy.models import Policy

router = APIRouter()


def _extension_field(body: dict, key: str) -> str | None:
    """Read an optional field from the ControlPlane-only "controlplane"
    extension object clients may include in the request body."""
    extension = body.get("controlplane")
    return extension.get(key) if isinstance(extension, dict) else None


def _resolve_tenant(request: Request, body: dict) -> str:
    return (
        request.headers.get("x-controlplane-tenant")
        or _extension_field(body, "tenant")
        or request.app.state.default_tenant
    )


@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    if not isinstance(body, dict) or "messages" not in body:
        raise HTTPException(status_code=400, detail="request body must include 'messages'")

    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    tenant_id = _resolve_tenant(request, body)

    policies: dict[str, Policy] = request.app.state.policies
    policy = policies.get(tenant_id)
    if policy is None:
        raise HTTPException(status_code=400, detail=f"unknown tenant '{tenant_id}'")

    # Strip the ControlPlane-only extension field before forwarding upstream.
    upstream_payload = {k: v for k, v in body.items() if k != "controlplane"}

    sessionmaker = request.app.state.sessionmaker
    provider = request.app.state.provider

    start = time.perf_counter()
    decision = "ALLOW"
    error: str | None = None
    upstream_response: dict | None = None

    try:
        upstream_response = await provider.chat_completion(upstream_payload)
    except ProviderError as exc:
        decision = "ERROR"
        error = str(exc)
    latency_ms = (time.perf_counter() - start) * 1000

    async with sessionmaker() as session:
        ledger = AuditLedger(session)
        await ledger.record(
            AuditRecord(
                request_id=request_id,
                tenant_id=tenant_id,
                policy_name=policy.tenant_id,
                decision=decision,
                conversation_id=_extension_field(body, "conversation_id"),
                latency_ms=latency_ms,
                error=error,
            )
        )

    if error is not None:
        raise HTTPException(status_code=502, detail=f"upstream provider error: {error}")

    assert upstream_response is not None
    upstream_response["controlplane"] = {
        "request_id": request_id,
        "tenant_id": tenant_id,
        "decision": decision,
        "latency_ms": round(latency_ms, 2),
    }
    return upstream_response
