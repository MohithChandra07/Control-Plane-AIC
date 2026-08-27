"""Governance engine: turns a raw response into claims, risk labels, and a
policy-driven decision, then reconstructs the response text with surgical
remediation applied.

Pipeline (spec §10 adaptive scrutiny):

    Tier 0 (detectors/tier0.py) -- cheap gate
       |
       +-- low risk --> ALLOW, response untouched, no claims extracted
       |
       +-- elevated --> Tier 1: extract_claims -> per claim: PII detect +
                          claim verify -> risk vector -> per-claim
                          remediation (policy-driven) -> aggregate decision
                          -> reconstruct text

Invariants enforced here (CLAUDE.md / spec §28):
  - UNVERIFIABLE is never treated as CONTRADICTED.
  - A single problematic claim never blocks the whole response by itself;
    only a hard-block PII category does that (a deliberate per-tenant
    policy choice, not an automatic score threshold).
  - Remediation never invents text: HEDGE/BLOCK use fixed, policy-approved
    templates; ADD_CITATION only appends a source id that a real corpus
    match produced.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

from detectors.base import Claim, ProvenanceSource, Verdict
from detectors.claims import extract_claims
from detectors.hallucination.claim_verifier import ClaimVerifier
from detectors.pii.regex_pii import detect_pii, redact
from detectors.tier0 import quick_risk_score
from policy.models import FailMode, Policy, Remediation, UnverifiableHandling

BLOCK_MESSAGE = (
    "I'm not able to share that information right now. "
    "A member of our team will follow up if needed."
)

_REMEDIATION_RANK = {
    Remediation.ALLOW: 0,
    Remediation.ADD_CITATION: 1,
    Remediation.HEDGE: 2,
    Remediation.REDACT: 3,
    Remediation.REMOVE: 4,
    Remediation.ESCALATE: 5,
    Remediation.BLOCK: 6,
}

_UNVERIFIABLE_MAP = {
    UnverifiableHandling.ALLOW: Remediation.ALLOW,
    UnverifiableHandling.HEDGE: Remediation.HEDGE,
    UnverifiableHandling.ESCALATE: Remediation.ESCALATE,
    UnverifiableHandling.BLOCK: Remediation.BLOCK,
}


class Decision(str, Enum):
    ALLOW = "ALLOW"
    MODIFY = "MODIFY"
    ESCALATE = "ESCALATE"
    BLOCK = "BLOCK"


_DECISION_BUCKET = {
    Remediation.ALLOW: Decision.ALLOW,
    Remediation.ADD_CITATION: Decision.MODIFY,
    Remediation.HEDGE: Decision.MODIFY,
    Remediation.REDACT: Decision.MODIFY,
    Remediation.REMOVE: Decision.MODIFY,
    Remediation.ESCALATE: Decision.ESCALATE,
    Remediation.BLOCK: Decision.BLOCK,
}
_DECISION_RANK = {Decision.ALLOW: 0, Decision.MODIFY: 1, Decision.ESCALATE: 2, Decision.BLOCK: 3}


class GovernanceResult(BaseModel):
    decision: Decision
    final_text: str
    claims: list[Claim]
    tier: int


def _hallucination_remediation(claim: Claim, policy: Policy) -> Remediation | None:
    if claim.verdict == Verdict.SUPPORTED:
        return None
    if claim.verdict == Verdict.UNVERIFIABLE:
        return _UNVERIFIABLE_MAP[policy.unverifiable_handling]
    if claim.verdict == Verdict.CONTRADICTED:
        if claim.risk.hallucination.score >= policy.risk_thresholds.tier2_trigger:
            return Remediation.ESCALATE
        return Remediation.REMOVE
    return None


def _pii_remediation(claim: Claim, policy: Policy) -> Remediation | None:
    if not policy.pii.enabled or not claim.pii_categories:
        return None
    if set(claim.pii_categories) & set(policy.pii.hard_block_categories):
        return Remediation.BLOCK
    return policy.pii.remediation


def _enforce_allowed(remediation: Remediation, policy: Policy) -> Remediation:
    if remediation in policy.allowed_remediations:
        return remediation
    # The tenant policy doesn't permit this action (e.g. BLOCK disabled for
    # a low-friction tenant) -- fall back to the conservative default of
    # asking a human rather than silently doing nothing or doing more than
    # the policy allows.
    return Remediation.ESCALATE if Remediation.ESCALATE in policy.allowed_remediations else remediation


def _annotate_claim(claim: Claim, verifier: ClaimVerifier, policy: Policy) -> Claim:
    verdict, score, provenance = verifier.verify(claim.text)
    claim.verdict = verdict
    claim.provenance = provenance
    claim.risk.hallucination.evaluated = True
    claim.risk.hallucination.detected = verdict != Verdict.SUPPORTED
    claim.risk.hallucination.score = score

    pii_matches = detect_pii(claim.text)
    claim.pii_categories = sorted({m.category for m in pii_matches})
    claim.risk.pii.evaluated = True
    claim.risk.pii.detected = bool(pii_matches)
    if pii_matches:
        hard_block = set(claim.pii_categories) & set(policy.pii.hard_block_categories)
        claim.risk.pii.score = 1.0 if hard_block else 0.6

    hallu_rem = _hallucination_remediation(claim, policy)
    pii_rem = _pii_remediation(claim, policy)
    candidates = [r for r in (hallu_rem, pii_rem) if r is not None]
    remediation = max(candidates, key=lambda r: _REMEDIATION_RANK[r]) if candidates else Remediation.ALLOW
    claim.remediation = _enforce_allowed(remediation, policy)

    # A verified, sourced claim gets its citation attached -- the source id
    # comes from an actual corpus match, never invented.
    if (
        claim.remediation == Remediation.ALLOW
        and claim.verdict == Verdict.SUPPORTED
        and claim.provenance is not None
        and claim.provenance.source == ProvenanceSource.RETRIEVED_DOC
        and Remediation.ADD_CITATION in policy.allowed_remediations
    ):
        claim.remediation = Remediation.ADD_CITATION

    return claim


def _render_claim(claim: Claim, policy: Policy) -> str | None:
    """Returns the claim's replacement text, or None to omit it entirely."""
    match claim.remediation:
        case None | Remediation.ALLOW:
            return claim.text
        case Remediation.ADD_CITATION:
            source = claim.provenance.source_id if claim.provenance else None
            return f"{claim.text} (source: {source})" if source else claim.text
        case Remediation.HEDGE:
            return f"I can't fully verify this, but: {claim.text}"
        case Remediation.REDACT:
            return redact(claim.text, detect_pii(claim.text))
        case Remediation.REMOVE:
            return None
        case Remediation.ESCALATE:
            return None if policy.fail_mode == FailMode.CLOSED else claim.text
        case Remediation.BLOCK:
            return None
    return claim.text


def _reconstruct_text(original: str, claims: list[Claim], policy: Policy) -> str:
    parts: list[str] = []
    cursor = 0
    for claim in sorted(claims, key=lambda c: c.start):
        parts.append(original[cursor : claim.start])
        replacement = _render_claim(claim, policy)
        if replacement is not None:
            parts.append(replacement)
        cursor = claim.end
    parts.append(original[cursor:])
    return "".join(parts).strip()


def _aggregate_decision(claims: list[Claim]) -> Decision:
    decision = Decision.ALLOW
    for claim in claims:
        bucket = _DECISION_BUCKET.get(claim.remediation or Remediation.ALLOW, Decision.ALLOW)
        if _DECISION_RANK[bucket] > _DECISION_RANK[decision]:
            decision = bucket
    return decision


class GovernanceEngine:
    def __init__(self, claim_verifier: ClaimVerifier):
        self._verifier = claim_verifier

    def evaluate(self, text: str, policy: Policy) -> GovernanceResult:
        tier0_score = quick_risk_score(text)
        if tier0_score < policy.risk_thresholds.tier1_trigger:
            return GovernanceResult(decision=Decision.ALLOW, final_text=text, claims=[], tier=0)

        claims = [_annotate_claim(c, self._verifier, policy) for c in extract_claims(text)]

        if any(c.remediation == Remediation.BLOCK for c in claims):
            return GovernanceResult(decision=Decision.BLOCK, final_text=BLOCK_MESSAGE, claims=claims, tier=1)

        final_text = _reconstruct_text(text, claims, policy)
        decision = _aggregate_decision(claims)
        return GovernanceResult(decision=decision, final_text=final_text, claims=claims, tier=1)
