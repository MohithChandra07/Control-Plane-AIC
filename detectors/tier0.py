"""Tier 0: a cheap, regex-only gate deciding whether a response needs the
full Tier 1 pipeline (claim extraction, PII detection, claim verification)
at all.

This is the "adaptive scrutiny" cascade from spec §10: explicit,
configurable thresholds (policy.risk_thresholds.tier1_trigger), not "if it
feels risky, check more". A clean response (Scene 1: no digits, no PII
patterns) never pays for Tier 1's extra work; anything with a PII-shaped
substring or a meaningful amount of numeric content does.

Known simplification: because Tier 1 here is itself heuristic/regex-based
rather than a real ML call, the latency gap Tier 0 buys is small today. The
gating *mechanism* is real and configurable now; it starts paying off in
latency once Phase 2's detectors are swapped for the real NLI/PII models
the roadmap calls for.
"""

from __future__ import annotations

import re

from detectors.pii.regex_pii import quick_pii_scan

_DIGIT = re.compile(r"\d")


def quick_risk_score(text: str) -> float:
    score = 0.0

    if quick_pii_scan(text):
        score = max(score, 0.9)

    digit_count = len(_DIGIT.findall(text))
    if digit_count:
        score = max(score, 0.4 + min(0.3, digit_count * 0.05))

    return min(score, 1.0)
