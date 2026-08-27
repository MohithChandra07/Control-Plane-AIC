"""Shared claim/risk/provenance models produced by detectors and consumed by
the policy engine (policy/engine.py).

Phase 2 scope: hallucination (via detectors/hallucination/) and pii (via
detectors/pii/) are real, working detectors. toxicity/policy/bias are
represented in the schema (spec §5: risk labels are multi-label, not
mutually exclusive) but have no detector behind them yet — their
RiskFinding.evaluated is False, which callers must check before trusting
`detected`. Don't read evaluated=False as "clean"; it means "not run".
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from policy.models import Remediation


class Verdict(str, Enum):
    """Claim verification outcome. UNVERIFIABLE is never collapsed into
    CONTRADICTED — see spec §4 / CLAUDE.md invariant #2."""

    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNVERIFIABLE = "UNVERIFIABLE"


class ProvenanceSource(str, Enum):
    RETRIEVED_DOC = "retrieved_doc"
    MODEL_PRIOR = "model_prior"
    USER_INPUT = "user_input"


class Provenance(BaseModel):
    source: ProvenanceSource
    source_id: str | None = None  # e.g. corpus doc id when source=retrieved_doc
    verdict: Verdict
    turn_id: int | None = None


class RiskFinding(BaseModel):
    detected: bool = False
    score: float = Field(0.0, ge=0.0, le=1.0)
    evaluated: bool = True


class RiskVector(BaseModel):
    """Multi-label risk assessment for one claim. Categories are
    independent — a claim can be both hallucination=true and pii=true at
    once (spec §5 example)."""

    hallucination: RiskFinding = Field(default_factory=RiskFinding)
    pii: RiskFinding = Field(default_factory=RiskFinding)
    policy: RiskFinding = Field(default_factory=lambda: RiskFinding(evaluated=False))
    toxicity: RiskFinding = Field(default_factory=lambda: RiskFinding(evaluated=False))
    bias: RiskFinding = Field(default_factory=lambda: RiskFinding(evaluated=False))

    def active_labels(self) -> list[str]:
        """Labels that were both evaluated and fired. Used for audit
        logging and the block/hard-block PII check."""
        return [
            name
            for name, finding in (
                ("hallucination", self.hallucination),
                ("pii", self.pii),
                ("policy", self.policy),
                ("toxicity", self.toxicity),
                ("bias", self.bias),
            )
            if finding.evaluated and finding.detected
        ]


class Claim(BaseModel):
    """One atomic factual claim extracted from a response, annotated as the
    governance pipeline (detectors/, policy/engine.py) runs."""

    claim_id: str
    text: str
    start: int
    end: int

    verdict: Verdict | None = None
    risk: RiskVector = Field(default_factory=RiskVector)
    provenance: Provenance | None = None
    pii_categories: list[str] = Field(default_factory=list)

    turn_id: int | None = None
    remediation: Remediation | None = None
    # Populated from Phase 3 onward (taint propagation across turns/tool
    # calls). Phase 2 claims are never annotated with taint.
    taint_status: str | None = None
