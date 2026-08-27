from gateway.middleware.cost_breaker import CostBreaker, estimate_tokens
from policy.models import CostBreakerPolicy


def test_allows_requests_within_budget():
    breaker = CostBreaker()
    policy = CostBreakerPolicy(max_requests_per_window=3, max_tokens_per_window=1000)
    for _ in range(3):
        assert breaker.check_and_record("tenant-a", 10, policy) is True


def test_trips_on_request_count():
    breaker = CostBreaker()
    policy = CostBreakerPolicy(max_requests_per_window=2, max_tokens_per_window=1000)
    assert breaker.check_and_record("tenant-a", 10, policy) is True
    assert breaker.check_and_record("tenant-a", 10, policy) is True
    assert breaker.check_and_record("tenant-a", 10, policy) is False  # retry storm


def test_trips_on_token_spike():
    breaker = CostBreaker()
    policy = CostBreakerPolicy(max_requests_per_window=100, max_tokens_per_window=50)
    assert breaker.check_and_record("tenant-a", 30, policy) is True
    assert breaker.check_and_record("tenant-a", 30, policy) is False  # would exceed 50 tokens


def test_disabled_breaker_never_trips():
    breaker = CostBreaker()
    policy = CostBreakerPolicy(enabled=False, max_requests_per_window=1, max_tokens_per_window=1)
    for _ in range(5):
        assert breaker.check_and_record("tenant-a", 1000, policy) is True


def test_tenants_are_isolated():
    breaker = CostBreaker()
    policy = CostBreakerPolicy(max_requests_per_window=1, max_tokens_per_window=1000)
    assert breaker.check_and_record("tenant-a", 10, policy) is True
    assert breaker.check_and_record("tenant-a", 10, policy) is False
    assert breaker.check_and_record("tenant-b", 10, policy) is True  # separate budget


def test_estimate_tokens_is_positive_for_nonempty_text():
    assert estimate_tokens("") >= 1
    assert estimate_tokens("a" * 40) >= 10
