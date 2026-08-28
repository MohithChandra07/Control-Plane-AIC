"""Risk appetite sweep (spec §20: risk appetite must move real metrics,
not be a cosmetic slider).

    python -m bench.harness.run_appetite_sweep

Runs the same 400-item labeled dataset (bench/dataset/generate.py) through
the real gateway at five appetite settings, applying policy.appetite's
apply_risk_appetite() on top of each tenant's real configured policy (not
a hypothetical one), and reports real, measured hallucination
recall/precision, escalation rate, and latency at each setting. Cost
breaker and model routing are disabled here for the same reason
bench/harness/run_benchmark.py disables them: isolating the mechanism
under test from unrelated ones.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

from bench.dataset.generate import generate_dataset
from bench.harness.run_benchmark import HarnessProvider, _completion
from bench.metrics.metrics import confusion_counts, escalation_rate, percentile
from gateway.main import create_app
from policy.appetite import apply_risk_appetite

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
APPETITES = [0.1, 0.3, 0.5, 0.7, 0.9]


def _run_appetite(appetite: float, items, db_path: Path) -> dict:
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    provider = HarnessProvider()
    app = create_app(provider=provider, engine=engine, run_migrations=True)

    latencies_ms: list[float] = []
    predicted_hallu: list[bool] = []
    actual_hallu: list[bool] = []
    decisions: list[str] = []
    tier1_count = 0

    with TestClient(app) as client:
        for tenant_id, policy in list(client.app.state.policies.items()):
            adjusted = apply_risk_appetite(policy, appetite)
            adjusted = adjusted.model_copy(
                update={
                    "cost_breaker": adjusted.cost_breaker.model_copy(update={"enabled": False}),
                    "model_routing": adjusted.model_routing.model_copy(update={"enabled": False}),
                }
            )
            client.app.state.policies[tenant_id] = adjusted

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
            detected = any("hallucination" in c["risk_labels"] for c in claims)
            if item.grounded is not None:
                predicted_hallu.append(detected)
                actual_hallu.append(not item.grounded)

    counts = confusion_counts(predicted_hallu, actual_hallu)
    return {
        "appetite": appetite,
        "tier1_invocation_rate": tier1_count / len(items),
        "escalation_rate": escalation_rate(decisions),
        "latency_ms": {"p50": percentile(latencies_ms, 50), "p95": percentile(latencies_ms, 95)},
        "hallucination_detection": counts.as_dict(),
    }


def _print_summary(results: list[dict]) -> None:
    header = f"{'appetite':<10}{'tier1_rate':>12}{'escalate':>10}{'p50_ms':>9}{'p95_ms':>9}{'hallu_recall':>14}{'hallu_precision':>17}"
    print(header)
    print("-" * len(header))
    for r in results:
        recall = r["hallucination_detection"]["recall"]
        precision = r["hallucination_detection"]["precision"]
        print(
            f"{r['appetite']:<10.1f}"
            f"{r['tier1_invocation_rate']:>12.2%}"
            f"{(r['escalation_rate'] or 0):>10.2%}"
            f"{r['latency_ms']['p50']:>9.2f}"
            f"{r['latency_ms']['p95']:>9.2f}"
            f"{(recall or 0):>14.2%}"
            f"{(precision if precision is not None else 0):>17.2%}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=400)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=RESULTS_DIR / "appetite_sweep_results.json")
    args = parser.parse_args()

    items = generate_dataset(count=args.count, seed=args.seed)
    print(f"generated {len(items)} labeled interactions (seed={args.seed})\n")

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        results = []
        for appetite in APPETITES:
            print(f"running appetite={appetite}...")
            results.append(_run_appetite(appetite, items, Path(tmp) / f"appetite_{appetite}.db"))

    print()
    _print_summary(results)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as f:
        json.dump({"seed": args.seed, "count": args.count, "results": results}, f, indent=2)
    print(f"\nwrote results to {args.out}")


if __name__ == "__main__":
    main()
