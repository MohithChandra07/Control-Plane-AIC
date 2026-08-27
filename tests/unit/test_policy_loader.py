import pytest
from pydantic import ValidationError

from policy.loader import PolicyLoadError, load_all_policies, load_policy
from policy.models import FailMode, Policy, UnverifiableHandling


def test_load_all_three_tenants():
    policies = load_all_policies()
    assert set(policies) == {"customer_support", "internal_copilot", "regulated_agent"}
    for policy in policies.values():
        assert isinstance(policy, Policy)


def test_customer_support_is_conservative():
    policy = load_policy("customer_support")
    assert policy.latency_budget_ms == 150
    assert policy.unverifiable_handling == UnverifiableHandling.HEDGE
    assert policy.fail_mode == FailMode.CLOSED


def test_internal_copilot_is_more_tolerant_than_customer_support():
    internal = load_policy("internal_copilot")
    support = load_policy("customer_support")
    assert internal.latency_budget_ms > support.latency_budget_ms
    assert internal.risk_thresholds.block_trigger > support.risk_thresholds.block_trigger
    assert internal.unverifiable_handling == UnverifiableHandling.ALLOW


def test_regulated_agent_has_tool_calls_enabled_and_strictest_thresholds():
    regulated = load_policy("regulated_agent")
    support = load_policy("customer_support")
    assert regulated.tool_calls.enabled is True
    assert "money_movement" in regulated.tool_calls.consequential_sinks
    assert regulated.risk_thresholds.tier1_trigger < support.risk_thresholds.tier1_trigger


def test_missing_tenant_raises():
    with pytest.raises(PolicyLoadError):
        load_policy("does_not_exist")


def test_threshold_ordering_is_validated():
    with pytest.raises(ValidationError):
        Policy(
            tenant_id="broken",
            display_name="Broken",
            latency_budget_ms=100,
            risk_thresholds={
                "tier1_trigger": 0.9,
                "tier2_trigger": 0.5,
                "block_trigger": 0.95,
            },
        )
