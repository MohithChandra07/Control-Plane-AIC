"""OpenAI-compatible /v1/chat/completions endpoint.

Phase 2 scope: resolve the tenant's policy, forward the request to the
upstream provider, run the response through the governance engine
(policy/engine.py -- Tier 0/1 adaptive scrutiny, claim extraction,
verification, PII detection, surgical remediation), and audit both the
request-level decision and each claim's outcome.

Only `choices[0].message.content` is governed; other choices (n>1) and
tool-call-only responses pass through ungoverned -- multi-choice and
tool-call gating are out of scope until Phase 3.
"""

from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, HTTPException, Request

from gateway.providers.base import ProviderError
from ledger.audit import AuditLedger, AuditRecord
from policy.engine import Decision, GovernanceResult
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


def _message_content(upstream_response: dict) -> str | None:
    choices = upstream_response.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    return content if isinstance(content, str) else None


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
    governance_engine = request.app.state.governance_engine

    start = time.perf_counter()
    error: str | None = None
    upstream_response: dict | None = None
    governance: GovernanceResult | None = None

    try:
        upstream_response = await provider.chat_completion(upstream_payload)
    except ProviderError as exc:
        error = str(exc)

    if error is None:
        assert upstream_response is not None
        content = _message_content(upstream_response)
        if content is not None:
            governance = governance_engine.evaluate(content, policy)
            upstream_response["choices"][0]["message"]["content"] = governance.final_text

    latency_ms = (time.perf_counter() - start) * 1000
    decision = "ERROR" if error is not None else governance.decision.value if governance else Decision.ALLOW.value
    conversation_id = _extension_field(body, "conversation_id")

    async with sessionmaker() as session:
        ledger = AuditLedger(session)
        await ledger.record(
            AuditRecord(
                request_id=request_id,
                tenant_id=tenant_id,
                policy_name=policy.tenant_id,
                decision=decision,
                conversation_id=conversation_id,
                latency_ms=latency_ms,
                error=error,
            )
        )
        if governance is not None:
            for claim in governance.claims:
                await ledger.record(
                    AuditRecord(
                        request_id=request_id,
                        tenant_id=tenant_id,
                        policy_name=policy.tenant_id,
                        decision=decision,
                        conversation_id=conversation_id,
                        claim_id=claim.claim_id,
                        verdict=claim.verdict.value if claim.verdict else None,
                        risk_labels=claim.risk.model_dump(),
                        provenance=claim.provenance.model_dump() if claim.provenance else None,
                        taint_status=claim.taint_status,
                        remediation=claim.remediation.value if claim.remediation else None,
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
        "tier": governance.tier if governance else 0,
        "claims": [
            {
                "claim_id": c.claim_id,
                "text": c.text,
                "verdict": c.verdict.value if c.verdict else None,
                "risk_labels": c.risk.active_labels(),
                "remediation": c.remediation.value if c.remediation else None,
            }
            for c in (governance.claims if governance else [])
        ],
    }
    return upstream_response
