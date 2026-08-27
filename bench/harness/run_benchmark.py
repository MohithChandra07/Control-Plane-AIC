"""Benchmark harness (spec §18; Phase 4 DoD: "benchmark runs from one command").

    python -m bench.harness.run_benchmark

Runs the labeled synthetic dataset (bench/dataset/generate.py) through the
real gateway -- real GovernanceEngine, real PII detector, real claim
verifier, real policy engine -- under three scrutiny configurations, and
reports real, measured numbers. Nothing here is fabricated (CLAUDE.md rule
#2): precision/recall come from comparing the gateway's actual output
against ground truth generated deterministically; latency is wall-clock
measured around each request.

Cost note: all three configurations make exactly one (fake, scripted)
upstream provider call per interaction -- model routing and the cost
breaker are disabled for this benchmark so it isolates the Tier 0/1
scrutiny-depth tradeoff specifically (the cheap-model-reroute cost story
is Scene 6's job, tested separately). So the honest cost/latency proxy
that actually *does* vary between configurations here is how often Tier 1
runs (tier1_invocation_rate) and the gateway's own processing latency --
not a dollar figure, which wouldn't differ across configs by construction
and would be misleading to report as if it did.

Only hallucination and PII detection get precision/recall: those are the
only two risk categories with a real detector behind them. The dataset
also carries policy_violation ground truth (spec's required coverage) but
no metric is computed for it -- see bench/metrics/metrics.py.

Also reports Expected Calibration Error (spec §19) for the hallucination
risk score: real (score, outcome) pairs collected from this same run,
binned and compared via bench/metrics/calibration.py. Only meaningful
because policy/engine.py's RiskFinding.score is a genuine risk magnitude
(0 for a confirmed-SUPPORTED claim) rather than "confidence in whichever
verdict came back" -- see that file for the bug this used to be.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

from bench.dataset.generate import DatasetItem, generate_dataset
from bench.metrics.calibration import expected_calibration_error
from bench.metrics.metrics import confusion_counts, escalation_rate, percentile
from gateway.main import create_app
from gateway.providers.base import Provider
from policy.models import Policy

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
MODES = ["ALWAYS_SHALLOW", "ALWAYS_DEEP", "ADAPTIVE"]


class HarnessProvider(Provider):
    """Returns whatever `next_response` is set to. Safe because the
    harness runs strictly sequentially -- one request is fully awaited
    before the next is prepared."""

    def __init__(self):
        self.next_response: dict[str, Any] | None = None
        self.call_count = 0

    async def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.call_count += 1
        assert self.next_response is not None
        return self.next_response


def _completion(content: str) -> dict:
    return {
        "id": "chatcmpl-bench",
        "object": "chat.completion",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
    }


def _override_policy(policy: Policy, mode: str) -> Policy:
    if mode == "ADAPTIVE":
        thresholds = policy.risk_thresholds
    elif mode == "ALWAYS_SHALLOW":
        # 1.0 is the max valid tier1_trigger -- Tier 1 only fires when
        # Tier 0's score hits the ceiling, which realistic content never
        # does (max ~0.9), so this is "never go deep" within the schema's
        # valid range.
        thresholds = policy.risk_thresholds.model_copy(update={"tier1_trigger": 1.0})
    elif mode == "ALWAYS_DEEP":
        thresholds = policy.risk_thresholds.model_copy(update={"tier1_trigger": 0.0})
    else:
        raise ValueError(f"unknown mode: {mode}")

    return policy.model_copy(
        update={
            "risk_thresholds": thresholds,
            "cost_breaker": policy.cost_breaker.model_copy(update={"enabled": False}),
            "model_routing": policy.model_routing.model_copy(update={"enabled": False}),
        }
    )


def _run_config(mode: str, items: list[DatasetItem], db_path: Path) -> dict:
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    provider = HarnessProvider()
    app = create_app(provider=provider, engine=engine, run_migrations=True)

    latencies_ms: list[float] = []
    predicted_hallu: list[bool] = []
    actual_hallu: list[bool] = []
    predicted_pii: list[bool] = []
    actual_pii: list[bool] = []
    hallu_scores: list[float] = []
    hallu_score_outcomes: list[bool] = []
    decisions: list[str] = []
    tier1_count = 0

    with TestClient(app) as client:
        for tenant_id, policy in list(client.app.state.policies.items()):
            client.app.state.policies[tenant_id] = _override_policy(policy, mode)

        for item in items:
            provider.next_response = _completion(item.response_text)
            payload = {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": item.prompt}],
                "controlplane": {"conversation_id": item.id},
            }
            start = time.perf_counter()
            response = client.post(
                "/v1/chat/completions", json=payload, headers={"x-controlplane-tenant": item.tenant}
            )
            latencies_ms.append((time.perf_counter() - start) * 1000)

            cp = response.json()["controlplane"]
            decisions.append(cp["decision"])
            if cp["tier"] == 1:
                tier1_count += 1

            claims = cp["claims"]
            detected_hallucination = any("hallucination" in c["risk_labels"] for c in claims)
            detected_pii = any("pii" in c["risk_labels"] for c in claims)

            if item.grounded is not None:
                predicted_hallu.append(detected_hallucination)
                actual_hallu.append(not item.grounded)
                if claims:
                    # One dataset item -> one primary claim by design; take
                    # the strongest hallucination score among any claims
                    # extracted (Tier 0 skips give an empty list, meaning
                    # no risk score was ever produced -- excluded here,
                    # same as ALWAYS_SHALLOW's 0% recall already shows).
                    hallu_scores.append(max(c["risk"]["hallucination"]["score"] for c in claims))
                    hallu_score_outcomes.append(not item.grounded)

            predicted_pii.append(detected_pii)
            actual_pii.append(item.has_pii)

    hallu_counts = confusion_counts(predicted_hallu, actual_hallu)
    pii_counts = confusion_counts(predicted_pii, actual_pii)
    hallu_ece = expected_calibration_error(hallu_scores, hallu_score_outcomes)

    return {
        "mode": mode,
        "interactions": len(items),
        "tier1_invocation_rate": tier1_count / len(items),
        "escalation_rate": escalation_rate(decisions),
        "decision_counts": dict(Counter(decisions)),
        "latency_ms": {
            "p50": percentile(latencies_ms, 50),
            "p95": percentile(latencies_ms, 95),
            "mean": statistics.mean(latencies_ms) if latencies_ms else None,
        },
        "hallucination_detection": hallu_counts.as_dict(),
        "pii_detection": pii_counts.as_dict(),
        "hallucination_calibration": {
            "ece": hallu_ece,
            "n_scored": len(hallu_scores),
        },
    }


def _print_summary(results: list[dict]) -> None:
    header = (
        f"{'mode':<15}{'tier1_rate':>12}{'escalate':>10}{'p50_ms':>9}{'p95_ms':>9}"
        f"{'hallu_recall':>14}{'pii_recall':>12}{'hallu_ece':>11}"
    )
    print(header)
    print("-" * len(header))
    for r in results:
        hallu_recall = r["hallucination_detection"]["recall"]
        pii_recall = r["pii_detection"]["recall"]
        ece = r["hallucination_calibration"]["ece"]
        print(
            f"{r['mode']:<15}"
            f"{r['tier1_invocation_rate']:>12.2%}"
            f"{(r['escalation_rate'] or 0):>10.2%}"
            f"{r['latency_ms']['p50']:>9.2f}"
            f"{r['latency_ms']['p95']:>9.2f}"
            f"{(hallu_recall or 0):>14.2%}"
            f"{(pii_recall or 0):>12.2%}"
            f"{(f'{ece:.3f}' if ece is not None else 'n/a'):>11}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=400)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=RESULTS_DIR / "benchmark_results.json")
    parser.add_argument("--db-dir", type=Path, default=None, help="dir for per-run sqlite files (default: temp)")
    args = parser.parse_args()

    items = generate_dataset(count=args.count, seed=args.seed)
    print(f"generated {len(items)} labeled interactions (seed={args.seed})\n")

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        db_dir = args.db_dir or Path(tmp)
        results = []
        for mode in MODES:
            print(f"running {mode}...")
            db_path = db_dir / f"{mode.lower()}.db"
            results.append(_run_config(mode, items, db_path))

    print()
    _print_summary(results)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as f:
        json.dump({"seed": args.seed, "count": args.count, "results": results}, f, indent=2)
    print(f"\nwrote results to {args.out}")


if __name__ == "__main__":
    main()
