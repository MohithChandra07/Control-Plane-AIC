"""Calibration analysis (spec §19): does a risk score of 0.90 actually
correspond to observed outcomes being risky ~90% of the time?

Computed from real (score, outcome) pairs collected during an actual
benchmark run (bench/harness/run_benchmark.py) against the labeled
synthetic dataset -- never fabricated, and only meaningful because
policy/engine.py's RiskFinding.score is a genuine risk magnitude (0 =
no risk, not "confidence in whichever verdict came back" -- see the
comment where hallucination.score is set in policy/engine.py for the bug
this used to be).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CalibrationBin:
    lower: float
    upper: float
    count: int
    avg_confidence: float | None
    observed_frequency: float | None  # fraction of this bin's items where outcome was True


def reliability_bins(scores: list[float], outcomes: list[bool], n_bins: int = 10) -> list[CalibrationBin]:
    if len(scores) != len(outcomes):
        raise ValueError("scores and outcomes must be the same length")

    bins: list[CalibrationBin] = []
    for i in range(n_bins):
        lower, upper = i / n_bins, (i + 1) / n_bins
        indices = [
            j
            for j, s in enumerate(scores)
            if (lower <= s < upper) or (i == n_bins - 1 and s == upper)
        ]
        if not indices:
            bins.append(CalibrationBin(lower, upper, 0, None, None))
            continue
        bin_scores = [scores[j] for j in indices]
        bin_outcomes = [outcomes[j] for j in indices]
        bins.append(
            CalibrationBin(
                lower=lower,
                upper=upper,
                count=len(indices),
                avg_confidence=sum(bin_scores) / len(bin_scores),
                observed_frequency=sum(bin_outcomes) / len(bin_outcomes),
            )
        )
    return bins


def expected_calibration_error(scores: list[float], outcomes: list[bool], n_bins: int = 10) -> float | None:
    """Standard ECE: the count-weighted average gap between each bin's
    average predicted score and its observed positive rate. 0 = perfectly
    calibrated; 1 = maximally miscalibrated."""
    bins = reliability_bins(scores, outcomes, n_bins)
    total = sum(b.count for b in bins)
    if total == 0:
        return None

    error = 0.0
    for b in bins:
        if b.count == 0 or b.avg_confidence is None or b.observed_frequency is None:
            continue
        error += (b.count / total) * abs(b.avg_confidence - b.observed_frequency)
    return error
