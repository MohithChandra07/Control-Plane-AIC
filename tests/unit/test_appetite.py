import pytest

from policy.appetite import apply_risk_appetite
from policy.loader import load_policy


@pytest.fixture
def policy():
    return load_policy("customer_support")


def test_appetite_half_is_a_no_op(policy):
    result = apply_risk_appetite(policy, 0.5)
    assert result.risk_thresholds == policy.risk_thresholds


def test_lower_appetite_relaxes_thresholds_upward(policy):
    result = apply_risk_appetite(policy, 0.0)
    assert result.risk_thresholds.tier1_trigger > policy.risk_thresholds.tier1_trigger
    assert result.risk_thresholds.tier2_trigger > policy.risk_thresholds.tier2_trigger
    assert result.risk_thresholds.block_trigger > policy.risk_thresholds.block_trigger


def test_higher_appetite_tightens_thresholds_downward(policy):
    result = apply_risk_appetite(policy, 1.0)
    assert result.risk_thresholds.tier1_trigger < policy.risk_thresholds.tier1_trigger
    assert result.risk_thresholds.tier2_trigger < policy.risk_thresholds.tier2_trigger
    assert result.risk_thresholds.block_trigger < policy.risk_thresholds.block_trigger


@pytest.mark.parametrize("appetite", [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0])
def test_threshold_ordering_is_always_preserved(policy, appetite):
    result = apply_risk_appetite(policy, appetite)
    t = result.risk_thresholds
    assert t.tier1_trigger <= t.tier2_trigger <= t.block_trigger


def test_extreme_appetites_stay_in_bounds(policy):
    low = apply_risk_appetite(policy, 0.0)
    high = apply_risk_appetite(policy, 1.0)
    for t in (low.risk_thresholds, high.risk_thresholds):
        assert 0.0 <= t.tier1_trigger <= 1.0
        assert 0.0 <= t.tier2_trigger <= 1.0
        assert 0.0 <= t.block_trigger <= 1.0


def test_out_of_range_appetite_raises(policy):
    with pytest.raises(ValueError):
        apply_risk_appetite(policy, 1.5)
    with pytest.raises(ValueError):
        apply_risk_appetite(policy, -0.1)


def test_appetite_does_not_erase_relative_tenant_differentiation():
    """A tenant configured stricter than another stays relatively
    stricter at the same appetite setting -- appetite scales relative to
    each tenant's own baseline, it doesn't replace it with a universal
    threshold set."""
    support = load_policy("customer_support")
    regulated = load_policy("regulated_agent")
    assert regulated.risk_thresholds.tier1_trigger < support.risk_thresholds.tier1_trigger

    adjusted_support = apply_risk_appetite(support, 0.8)
    adjusted_regulated = apply_risk_appetite(regulated, 0.8)
    assert adjusted_regulated.risk_thresholds.tier1_trigger < adjusted_support.risk_thresholds.tier1_trigger


def test_other_policy_fields_are_untouched(policy):
    result = apply_risk_appetite(policy, 1.0)
    assert result.tenant_id == policy.tenant_id
    assert result.pii == policy.pii
    assert result.tool_calls == policy.tool_calls
    assert result.unverifiable_handling == policy.unverifiable_handling
