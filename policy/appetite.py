"""Risk appetite control (spec §20): a single scalar that actually moves
policy behavior -- not a cosmetic slider. Demonstrated to move false
positives/negatives, latency, and escalation rate on the real benchmark
dataset, not just asserted: see bench/harness/run_appetite_sweep.py.

appetite in [0.0, 1.0]:
    0.0 = most permissive  -- thresholds relax toward 1.0 (rarely fire)
    0.5 = the tenant's own configured thresholds, unchanged
    1.0 = strictest        -- thresholds tighten toward 0.0 (fire eagerly)

Scales the tenant's *own* configured risk_thresholds proportionally
rather than replacing them with a universal set, so a tenant configured
stricter than another (e.g. regulated_agent vs internal_copilot) stays
relatively stricter at every appetite setting -- appetite adjusts how
cautious a tenant is *relative to its own baseline*, it doesn't erase
the policy differentiation between tenants (spec invariant #11).
"""

from __future__ import annotations

from policy.models import Policy, RiskThresholds


def _scale(base: float, appetite: float) -> float:
    if appetite < 0.5:
        relax = (0.5 - appetite) / 0.5  # 0..1, 1 = fully relaxed toward 1.0
        return base + (1.0 - base) * relax
    if appetite > 0.5:
        tighten = (appetite - 0.5) / 0.5  # 0..1, 1 = fully tightened toward 0.0
        return base * (1.0 - tighten)
    return base


def apply_risk_appetite(policy: Policy, appetite: float) -> Policy:
    if not 0.0 <= appetite <= 1.0:
        raise ValueError("appetite must be in [0.0, 1.0]")
    if appetite == 0.5:
        return policy  # no-op: the tenant's configured thresholds stand as-is

    t = policy.risk_thresholds
    tier1 = max(0.0, min(1.0, _scale(t.tier1_trigger, appetite)))
    tier2 = max(tier1, min(1.0, _scale(t.tier2_trigger, appetite)))
    block = max(tier2, min(1.0, _scale(t.block_trigger, appetite)))

    new_thresholds = RiskThresholds(tier1_trigger=tier1, tier2_trigger=tier2, block_trigger=block)
    return policy.model_copy(update={"risk_thresholds": new_thresholds})
