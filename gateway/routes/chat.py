"""OpenAI-compatible /v1/chat/completions endpoint.

Phase 3 scope, on top of Phase 2's response governance:

  - Cost circuit breaker (spec §17, Scene 5): a per-tenant sliding-window
    check runs before the upstream provider is ever called; a tripped
    breaker short-circuits with 429, no provider call, no cost incurred.
  - Cheap-model reroute (spec §11, Scene 6): when enabled, the cheap model
    is tried first and validated by the same governance engine; only a
    flagged (ESCALATE/BLOCK) response triggers a retry against the
    stronger escalation model.
  - Tool-call gating (spec §9, Scene 7 -- the critical one): every
    tool_call in the response is checked against the tool sink catalog
    and, for consequential sinks, against ledger/taint.py for arguments
    that trace back to an unverified/contradicted claim earlier in this
    conversation. A tainted argument never silently reaches the
    application as a green-lit call.

Only `choices[0].message` is governed; other choices (n>1) pass through
ungoverned -- multi-choice is out of scope.
"""

from __future__ import annotations

import json
import time
import uuid

from fastapi import APIRouter, HTTPException, Request

from gateway.middleware.cost_breaker import estimate_tokens
from gateway.providers.base import ProviderError
from ledger.audit import AuditLedger, AuditRecord
from policy.engine import (
    Decision,
    GovernanceEngine,
    GovernanceResult,
    decision_rank,
    remediation_to_decision,
)
from policy.models import FailMode, Policy, Remediation
from policy.tool_gate import ToolCallDecision, gate_tool_call

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


def _turn_id(body: dict) -> int:
    messages = body.get("messages")
    if not isinstance(messages, list):
        return 1
    return max(1, sum(1 for m in messages if isinstance(m, dict) and m.get("role") == "user"))


def _prompt_text(body: dict) -> str:
    messages = body.get("messages")
    if not isinstance(messages, list):
        return ""
    return " ".join(
        m.get("content", "") for m in messages if isinstance(m, dict) and isinstance(m.get("content"), str)
    )


def _message(upstream_response: dict) -> dict | None:
    choices = upstream_response.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    return message if isinstance(message, dict) else None


def _message_content(upstream_response: dict) -> str | None:
    message = _message(upstream_response)
    content = message.get("content") if message else None
    return content if isinstance(content, str) else None


async def _call_model(provider, payload: dict, model: str | None) -> tuple[dict | None, str | None]:
    call_payload = {**payload, "model": model} if model else payload
    try:
        return await provider.chat_completion(call_payload), None
    except ProviderError as exc:
        return None, str(exc)


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

    conversation_id = _extension_field(body, "conversation_id")
    turn_id = _turn_id(body)
    sessionmaker = request.app.state.sessionmaker
    start = time.perf_counter()

    # --- Cost circuit breaker (Scene 5): checked before any provider call. ---
    tokens = estimate_tokens(_prompt_text(body))
    if not request.app.state.cost_breaker.check_and_record(tenant_id, tokens, policy.cost_breaker):
        latency_ms = (time.perf_counter() - start) * 1000
        async with sessionmaker() as session:
            await AuditLedger(session).record(
                AuditRecord(
                    request_id=request_id,
                    tenant_id=tenant_id,
                    policy_name=policy.tenant_id,
                    decision="BLOCK",
                    conversation_id=conversation_id,
                    turn_id=turn_id,
                    latency_ms=latency_ms,
                    error="cost circuit breaker tripped (retry storm / token spike protection)",
                )
            )
        raise HTTPException(status_code=429, detail="rate/cost limit exceeded for this tenant")

    upstream_payload = {k: v for k, v in body.items() if k != "controlplane"}
    provider = request.app.state.provider
    governance_engine: GovernanceEngine = request.app.state.governance_engine

    # --- Cheap-model reroute, validated by the governance engine (Scene 6). ---
    requested_model = upstream_payload.get("model")
    model_used = requested_model
    rerouted = False

    first_model = policy.model_routing.cheap_model if policy.model_routing.enabled else requested_model
    upstream_response, error = await _call_model(provider, upstream_payload, first_model)
    model_used = first_model
    governance: GovernanceResult | None = None
    if error is None:
        content = _message_content(upstream_response)
        if content is not None:
            governance = governance_engine.evaluate(content, policy, turn_id=turn_id)

    if (
        error is None
        and policy.model_routing.enabled
        and governance is not None
        and governance.decision in (Decision.ESCALATE, Decision.BLOCK)
    ):
        escalated_response, escalated_error = await _call_model(
            provider, upstream_payload, policy.model_routing.escalation_model
        )
        if escalated_error is None:
            content = _message_content(escalated_response)
            escalated_governance = (
                governance_engine.evaluate(content, policy, turn_id=turn_id) if content is not None else None
            )
            upstream_response = escalated_response
            governance = escalated_governance
            model_used = policy.model_routing.escalation_model
            rerouted = True
        # If the escalation call itself fails, we keep the cheap model's
        # (already flagged/remediated) response rather than losing the
        # turn entirely -- the flagged decision still applies below.

    if error is None:
        assert upstream_response is not None
        message = _message(upstream_response)
        if message is not None and governance is not None:
            message["content"] = governance.final_text

    # --- Tool-call gating (Scene 7 -- the critical one). ---
    tool_decisions: list[ToolCallDecision] = []
    decision_value = governance.decision if governance else Decision.ALLOW

    if error is None:
        message = _message(upstream_response)
        tool_calls = message.get("tool_calls") if message else None
        if isinstance(tool_calls, list) and tool_calls:
            kept_calls = []
            async with sessionmaker() as session:
                for call in tool_calls:
                    fn = call.get("function", {}) if isinstance(call, dict) else {}
                    name = fn.get("name")
                    try:
                        arguments = json.loads(fn.get("arguments", "{}"))
                    except (TypeError, ValueError):
                        arguments = {}
                    tool_decision = await gate_tool_call(
                        session,
                        conversation_id,
                        name,
                        arguments if isinstance(arguments, dict) else {},
                        policy,
                        request.app.state.tool_specs,
                    )
                    tool_decisions.append(tool_decision)

                    bucket = remediation_to_decision(tool_decision.decision)
                    if decision_rank(bucket) > decision_rank(decision_value):
                        decision_value = bucket

                    drop = tool_decision.decision == Remediation.BLOCK or (
                        tool_decision.decision == Remediation.ESCALATE and policy.fail_mode == FailMode.CLOSED
                    )
                    if not drop:
                        kept_calls.append(call)

            if message is not None:
                if kept_calls:
                    message["tool_calls"] = kept_calls
                else:
                    message.pop("tool_calls", None)

    latency_ms = (time.perf_counter() - start) * 1000
    decision = "ERROR" if error is not None else decision_value.value

    async with sessionmaker() as session:
        ledger = AuditLedger(session)
        await ledger.record(
            AuditRecord(
                request_id=request_id,
                tenant_id=tenant_id,
                policy_name=policy.tenant_id,
                decision=decision,
                conversation_id=conversation_id,
                turn_id=turn_id,
                latency_ms=latency_ms,
                error=error,
                action={"model_used": model_used, "rerouted": rerouted} if policy.model_routing.enabled else None,
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
                        turn_id=turn_id,
                        claim_id=claim.claim_id,
                        claim_text=claim.text,
                        verdict=claim.verdict.value if claim.verdict else None,
                        risk_labels=claim.risk.model_dump(),
                        provenance=claim.provenance.model_dump() if claim.provenance else None,
                        taint_status=claim.taint_status,
                        remediation=claim.remediation.value if claim.remediation else None,
                    )
                )
        for tool_decision in tool_decisions:
            await ledger.record(
                AuditRecord(
                    request_id=request_id,
                    tenant_id=tenant_id,
                    policy_name=policy.tenant_id,
                    decision=decision,
                    conversation_id=conversation_id,
                    turn_id=turn_id,
                    remediation=tool_decision.decision.value,
                    action={
                        "tool_name": tool_decision.tool_name,
                        "sink": tool_decision.sink,
                        "tainted_args": {
                            arg: match.claim_id for arg, match in tool_decision.tainted_args.items()
                        },
                    },
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
        "turn_id": turn_id,
        "model_used": model_used,
        "rerouted": rerouted,
        "claims": [
            {
                "claim_id": c.claim_id,
                "text": c.text,
                "verdict": c.verdict.value if c.verdict else None,
                "risk_labels": c.risk.active_labels(),
                "remediation": c.remediation.value if c.remediation else None,
                "taint_status": c.taint_status,
            }
            for c in (governance.claims if governance else [])
        ],
        "tool_calls": [
            {
                "tool_name": d.tool_name,
                "sink": d.sink,
                "decision": d.decision.value,
                "tainted_args": list(d.tainted_args.keys()),
            }
            for d in tool_decisions
        ],
    }
    return upstream_response
