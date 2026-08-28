"""Policy schema.

A Policy is the declarative, tenant-specific configuration that governs how
ControlPlane treats requests, claims, and tool calls. It is loaded from YAML
(see configs/) and never hard-coded in Python — see policy/loader.py.

The schema intentionally covers fields that later phases (claim
verification, remediation, tool-call gating) will read, even though Phase 1
only *loads and validates* policy — it does not yet enforce most of it.
Keeping the schema stable now avoids rewriting configs/*.yaml every phase.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class Remediation(str, Enum):
    ALLOW = "ALLOW"
    HEDGE = "HEDGE"
    REDACT = "REDACT"
    REMOVE = "REMOVE"
    ADD_CITATION = "ADD_CITATION"
    ESCALATE = "ESCALATE"
    BLOCK = "BLOCK"


class UnverifiableHandling(str, Enum):
    """How a claim with verdict UNVERIFIABLE should be treated.

    UNVERIFIABLE is never silently treated as CONTRADICTED (see
    docs/terminology.md) — this only controls the remediation applied.
    """

    ALLOW = "ALLOW"
    HEDGE = "HEDGE"
    ESCALATE = "ESCALATE"
    BLOCK = "BLOCK"


class FailMode(str, Enum):
    OPEN = "fail_open"
    CLOSED = "fail_closed"


class RiskThresholds(BaseModel):
    """Score thresholds (0.0-1.0) that move a claim between scrutiny tiers
    and that select a remediation when a risk label fires."""

    tier1_trigger: float = Field(0.4, ge=0.0, le=1.0)
    tier2_trigger: float = Field(0.75, ge=0.0, le=1.0)
    block_trigger: float = Field(0.9, ge=0.0, le=1.0)


class PiiPolicy(BaseModel):
    enabled: bool = True
    remediation: Remediation = Remediation.REDACT
    # PII categories treated as always-block regardless of remediation above
    # (e.g. government IDs, card numbers) — empty by default, set per tenant.
    hard_block_categories: list[str] = Field(default_factory=list)


class ToolCallPolicy(BaseModel):
    """Governs consequential tool-call/action gating (see ledger/taint.py)."""

    enabled: bool = False
    # Sink classes considered consequential for this tenant, e.g.
    # "money_movement", "database_write", "external_communication".
    consequential_sinks: list[str] = Field(default_factory=list)
    # What happens when a tool-call argument traces back to tainted
    # provenance.
    tainted_argument_action: Remediation = Remediation.BLOCK
    require_verified_provenance: bool = True


class EscalationPolicy(BaseModel):
    enabled: bool = True
    # Fraction of borderline decisions routed to a human reviewer, used by
    # adaptive scrutiny / calibration (bench/, console/) in later phases.
    max_escalation_rate: float = Field(0.2, ge=0.0, le=1.0)


class CostBreakerPolicy(BaseModel):
    """Circuit breaker against retry storms / token spikes (spec §17,
    Scene 5). Trips per-tenant when either limit is exceeded within the
    trailing window -- see gateway/middleware/cost_breaker.py."""

    enabled: bool = True
    window_seconds: int = Field(60, gt=0)
    max_requests_per_window: int = Field(60, gt=0)
    max_tokens_per_window: int = Field(100_000, gt=0)


class ModelRoutingPolicy(BaseModel):
    """Cheap-model-first routing, validated by the governance engine
    (spec §11 cost/quality tradeoff, Scene 6). When enabled, the gateway
    calls `cheap_model` first; if the governance engine's decision on that
    response is ESCALATE or BLOCK, it retries the same request against
    `escalation_model` and uses that response instead."""

    enabled: bool = False
    cheap_model: str = "gpt-4o-mini"
    escalation_model: str = "gpt-4o"


class Policy(BaseModel):
    """Full policy profile for one tenant, loaded from configs/<tenant>.yaml."""

    tenant_id: str
    display_name: str
    description: str = ""

    latency_budget_ms: int = Field(..., gt=0)

    allowed_remediations: list[Remediation] = Field(
        default_factory=lambda: list(Remediation)
    )
    unverifiable_handling: UnverifiableHandling = UnverifiableHandling.HEDGE

    risk_thresholds: RiskThresholds = Field(default_factory=RiskThresholds)
    pii: PiiPolicy = Field(default_factory=PiiPolicy)
    tool_calls: ToolCallPolicy = Field(default_factory=ToolCallPolicy)
    escalation: EscalationPolicy = Field(default_factory=EscalationPolicy)
    cost_breaker: CostBreakerPolicy = Field(default_factory=CostBreakerPolicy)
    model_routing: ModelRoutingPolicy = Field(default_factory=ModelRoutingPolicy)

    fail_mode: FailMode = FailMode.CLOSED

    @model_validator(mode="after")
    def _validate_thresholds_ordered(self) -> Policy:
        t = self.risk_thresholds
        if not (t.tier1_trigger <= t.tier2_trigger <= t.block_trigger):
            raise ValueError(
                "risk_thresholds must satisfy tier1_trigger <= tier2_trigger <= block_trigger"
            )
        return self
