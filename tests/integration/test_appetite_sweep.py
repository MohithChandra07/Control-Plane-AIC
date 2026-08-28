"""Smoke test for the appetite sweep harness itself: proves it runs and
that recall is monotonically non-decreasing as appetite increases (the
"not cosmetic" claim, spec §20) -- not that any specific number is exactly
right (that's bench/dataset + bench/metrics's job)."""

from pathlib import Path

from bench.dataset.generate import generate_dataset
from bench.harness.run_appetite_sweep import _run_appetite


def test_recall_is_monotonically_non_decreasing_with_appetite(tmp_path: Path):
    items = generate_dataset(count=60, seed=2)
    appetites = [0.1, 0.5, 0.9]
    recalls = []
    for appetite in appetites:
        result = _run_appetite(appetite, items, tmp_path / f"a{appetite}.db")
        recalls.append(result["hallucination_detection"]["recall"] or 0.0)

    assert recalls == sorted(recalls)


def test_tier1_rate_increases_with_appetite(tmp_path: Path):
    items = generate_dataset(count=60, seed=2)
    low = _run_appetite(0.1, items, tmp_path / "low.db")
    high = _run_appetite(0.9, items, tmp_path / "high.db")
    assert high["tier1_invocation_rate"] >= low["tier1_invocation_rate"]
