"""Recalibration suggestion from human review feedback (Scene 9: "human
reviewer override... proves feedback loop, threshold/calibration update").

Given collected human reviews of ESCALATE/BLOCK decisions, suggests a
directional threshold adjustment when humans disagree often enough that
the current threshold looks too aggressive. Deliberately a *suggestion*,
not an auto-apply: silently recalibrating a live safety threshold from a
small, possibly-biased sample of human reviews with no human confirming
the change would itself be an unaudited, unsupervised way to alter
governance behavior (CLAUDE.md rule #5) -- the suggestion still has to be
applied by a human via the same risk-appetite control (policy/appetite.py)
that's already audited.

This only detects "too aggressive" (reviewers overturning ESCALATE/BLOCK
calls). It can't detect "too lenient" from override data alone: reviews
only ever happen on decisions that were already flagged, so there's no
signal here about hallucinations/PII that were *silently allowed* -- that
would need the console to also let reviewers flag missed cases, which
isn't implemented in Phase 5. Documented, not silently assumed away.
"""

from __future__ import annotations

from dataclasses import dataclass

_ESCALATION_DECISIONS = ("ESCALATE", "BLOCK")


@dataclass
class RecalibrationSuggestion:
    tenant_id: str
    reviewed_count: int
    disagreement_rate: float
    suggested_appetite_delta: float
    message: str


def suggest_recalibration(
    tenant_id: str,
    reviews: list[dict],
    disagreement_threshold: float = 0.3,
    min_reviews: int = 3,
    step: float = 0.1,
) -> RecalibrationSuggestion | None:
    """`reviews` is a list of {"decision": str, "agree": bool} -- the
    decision being reviewed and whether the human reviewer agreed with
    it. Only ESCALATE/BLOCK reviews count: those are the decisions with
    real friction cost, and the ones this heuristic can meaningfully
    reason about (see module docstring)."""

    escalations = [r for r in reviews if r.get("decision") in _ESCALATION_DECISIONS]
    if len(escalations) < min_reviews:
        return None

    disagree_rate = sum(1 for r in escalations if not r.get("agree")) / len(escalations)
    if disagree_rate <= disagreement_threshold:
        return None

    return RecalibrationSuggestion(
        tenant_id=tenant_id,
        reviewed_count=len(escalations),
        disagreement_rate=disagree_rate,
        suggested_appetite_delta=-step,
        message=(
            f"Reviewers disagreed with {disagree_rate:.0%} of ESCALATE/BLOCK decisions "
            f"for '{tenant_id}' (n={len(escalations)}). Consider lowering risk appetite by "
            f"~{step:.2f} to reduce over-escalation."
        ),
    )
