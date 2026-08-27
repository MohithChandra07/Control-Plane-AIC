"""Evaluation metrics (spec §18).

Pure functions over measured data -- nothing here invents a number. Every
metric is computed from real outcomes (a GovernanceEngine decision/verdict,
a measured latency, a measured call count) against real ground truth
(the labels a dataset item was generated with, per bench/dataset/generate.py).

Deliberately NOT implemented here (see docs/roadmap.md for why):
  - "human agreement" -- would require real human-labeled review data,
    which doesn't exist in this environment. Never fabricated.
  - Expected Calibration Error / reliability curves -- Phase 5 scope.
  - Any metric for the `policy_violation` ground-truth label -- the
    dataset carries it (spec's ground-truth coverage requirement), but no
    policy-violation detector exists yet, so there's nothing real to score.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConfusionCounts:
    true_positive: int = 0
    false_positive: int = 0
    true_negative: int = 0
    false_negative: int = 0

    @property
    def total(self) -> int:
        return self.true_positive + self.false_positive + self.true_negative + self.false_negative

    @property
    def precision(self) -> float | None:
        denom = self.true_positive + self.false_positive
        return self.true_positive / denom if denom else None

    @property
    def recall(self) -> float | None:
        denom = self.true_positive + self.false_negative
        return self.true_positive / denom if denom else None

    @property
    def f1(self) -> float | None:
        p, r = self.precision, self.recall
        if not p or not r or (p + r) == 0:
            return None
        return 2 * p * r / (p + r)

    def as_dict(self) -> dict:
        return {
            "tp": self.true_positive,
            "fp": self.false_positive,
            "tn": self.true_negative,
            "fn": self.false_negative,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
        }


def confusion_counts(predicted: list[bool], actual: list[bool]) -> ConfusionCounts:
    if len(predicted) != len(actual):
        raise ValueError("predicted and actual must be the same length")
    counts = ConfusionCounts()
    for p, a in zip(predicted, actual, strict=True):
        if p and a:
            counts.true_positive += 1
        elif p and not a:
            counts.false_positive += 1
        elif not p and a:
            counts.false_negative += 1
        else:
            counts.true_negative += 1
    return counts


def percentile(values: list[float], pct: float) -> float | None:
    """Nearest-rank percentile (pct in [0, 100]). No interpolation --
    simple and unambiguous for benchmark reporting."""
    if not values:
        return None
    if not 0 <= pct <= 100:
        raise ValueError("pct must be in [0, 100]")
    ordered = sorted(values)
    rank = max(1, round(pct / 100 * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


def escalation_rate(decisions: list[str]) -> float | None:
    if not decisions:
        return None
    return sum(1 for d in decisions if d == "ESCALATE") / len(decisions)


def estimated_cost_per_1000(
    total_tokens: int,
    interactions: int,
    price_per_1k_tokens: float,
) -> float | None:
    """Illustrative cost: measured token volume from an actual benchmark
    run (summed across every provider call an interaction triggered,
    including model-routing reroutes) x a configured (not measured)
    $/1K-token rate -- see bench/pricing.yaml. Never presented as real
    billing; no real provider call was made (the harness uses a scripted
    fake provider). Report avg calls/interaction separately to show the
    reroute cost tradeoff -- it's not folded into this number."""
    if interactions <= 0:
        return None
    cost_per_interaction = (total_tokens / 1000) * price_per_1k_tokens / interactions
    return cost_per_interaction * 1000
