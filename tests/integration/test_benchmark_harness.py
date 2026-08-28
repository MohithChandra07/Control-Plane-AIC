"""Smoke test for the benchmark harness itself: proves it actually runs
end-to-end (spec §23 Phase 4 DoD: "benchmark runs from one command") and
produces sane, real metrics -- not that any specific number is exactly
right (that's what the dataset/detector unit tests are for)."""

from pathlib import Path

from bench.dataset.generate import generate_dataset
from bench.harness.run_benchmark import MODES, _run_config


def test_all_three_configs_run_and_produce_metrics(tmp_path: Path):
    items = generate_dataset(count=24, seed=1)
    results = {mode: _run_config(mode, items, tmp_path / f"{mode}.db") for mode in MODES}

    for mode in MODES:
        r = results[mode]
        assert r["interactions"] == 24
        assert 0.0 <= r["tier1_invocation_rate"] <= 1.0
        assert r["latency_ms"]["p50"] is not None
        assert r["latency_ms"]["p50"] > 0


def test_always_shallow_never_invokes_tier1():
    items = generate_dataset(count=24, seed=1)
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        result = _run_config("ALWAYS_SHALLOW", items, Path(tmp) / "shallow.db")
    assert result["tier1_invocation_rate"] == 0.0


def test_always_deep_always_invokes_tier1():
    items = generate_dataset(count=24, seed=1)
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        result = _run_config("ALWAYS_DEEP", items, Path(tmp) / "deep.db")
    assert result["tier1_invocation_rate"] == 1.0


def test_adaptive_never_does_more_work_than_always_deep():
    items = generate_dataset(count=100, seed=1)
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        adaptive = _run_config("ADAPTIVE", items, Path(tmp) / "adaptive.db")
        deep = _run_config("ALWAYS_DEEP", items, Path(tmp) / "deep.db")
    assert adaptive["tier1_invocation_rate"] <= deep["tier1_invocation_rate"]
    assert deep["tier1_invocation_rate"] == 1.0
