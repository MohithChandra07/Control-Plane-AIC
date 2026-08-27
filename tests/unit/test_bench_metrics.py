from bench.metrics.metrics import (
    confusion_counts,
    escalation_rate,
    estimated_cost_per_1000,
    percentile,
)


def test_confusion_counts_basic():
    predicted = [True, True, False, False]
    actual = [True, False, True, False]
    counts = confusion_counts(predicted, actual)
    assert counts.true_positive == 1
    assert counts.false_positive == 1
    assert counts.false_negative == 1
    assert counts.true_negative == 1
    assert counts.precision == 0.5
    assert counts.recall == 0.5
    assert counts.f1 == 0.5


def test_confusion_counts_perfect_precision_and_recall():
    counts = confusion_counts([True, True], [True, True])
    assert counts.precision == 1.0
    assert counts.recall == 1.0
    assert counts.f1 == 1.0


def test_confusion_counts_no_positives_predicted_gives_none_precision():
    counts = confusion_counts([False, False], [True, False])
    assert counts.precision is None
    assert counts.recall == 0.0


def test_confusion_counts_mismatched_lengths_raises():
    try:
        confusion_counts([True], [True, False])
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_percentile_p50_and_p95():
    values = list(range(1, 101))  # 1..100
    assert percentile(values, 50) == 50
    assert percentile(values, 95) == 95


def test_percentile_empty_is_none():
    assert percentile([], 50) is None


def test_escalation_rate():
    assert escalation_rate(["ALLOW", "ESCALATE", "ESCALATE", "BLOCK"]) == 0.5
    assert escalation_rate([]) is None


def test_estimated_cost_per_1000_scales_with_tokens():
    cost_small = estimated_cost_per_1000(total_tokens=1000, interactions=10, price_per_1k_tokens=1.0)
    cost_large = estimated_cost_per_1000(total_tokens=2000, interactions=10, price_per_1k_tokens=1.0)
    assert cost_large == cost_small * 2
    assert cost_small == 100.0  # (1000/1000 * 1.0) / 10 * 1000


def test_estimated_cost_per_1000_zero_interactions_is_none():
    assert estimated_cost_per_1000(total_tokens=100, interactions=0, price_per_1k_tokens=1.0) is None
