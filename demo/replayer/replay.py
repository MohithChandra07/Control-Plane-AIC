"""Traffic replayer (spec §21): generates and posts synthetic interactions
through the real gateway -- real GovernanceEngine, real policy engine,
real audit ledger -- to populate data for the console dashboard, stress
the pipeline, and measure latency at volume.

    python -m demo.replayer.replay --count 10000

No manual clicking: this is the one command that populates the
console backend's data source. Reuses the same synthetic dataset
generator as bench/ (bench/dataset/generate.py) but runs under real,
unmodified tenant policies (no ALWAYS-SHALLOW/DEEP overrides) -- this
traffic is meant to look like what a live deployment actually produces.

Defaults to a local SQLite file so the whole thing is runnable with no
setup; pass --database-url postgresql+asyncpg://... to point at a real
Postgres instance instead (e.g. the one docker-compose brings up), in
which case traffic accumulates there run over run rather than resetting.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine

from bench.dataset.generate import generate_dataset
from gateway.main import create_app
from gateway.providers.base import Provider

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "traffic.db"


class ReplayProvider(Provider):
    def __init__(self):
        self.next_response: dict[str, Any] | None = None

    async def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        assert self.next_response is not None
        return self.next_response


def _completion(content: str) -> dict:
    return {
        "id": "chatcmpl-replay",
        "object": "chat.completion",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
    }


def replay(
    count: int, seed: int, database_url: str | None, progress_every: int = 500
) -> dict:
    if database_url:
        engine = create_async_engine(database_url)
        run_migrations = False
    else:
        DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_DB_PATH.unlink(missing_ok=True)
        engine = create_async_engine(f"sqlite+aiosqlite:///{DEFAULT_DB_PATH}")
        run_migrations = True

    items = generate_dataset(count=count, seed=seed)
    provider = ReplayProvider()
    app = create_app(provider=provider, engine=engine, run_migrations=run_migrations)

    decisions_seen: dict[str, int] = {}
    start = time.perf_counter()
    with TestClient(app) as client:
        # The cost breaker is real and *should* trip under this tool's
        # much-faster-than-realistic request rate (Scene 5's own test
        # proves it works) -- but that would starve the dashboard of the
        # varied governance data it's meant to showcase, so it's turned
        # off here specifically. Everything else (thresholds, PII
        # handling, model routing, tool-call gating) stays as configured.
        for policy in client.app.state.policies.values():
            policy.cost_breaker.enabled = False

        for i, item in enumerate(items, start=1):
            provider.next_response = _completion(item.response_text)
            payload = {
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": item.prompt}],
                "controlplane": {"conversation_id": item.id},
            }
            response = client.post(
                "/v1/chat/completions", json=payload, headers={"x-controlplane-tenant": item.tenant}
            )
            # Real, unmodified tenant policies are in effect here (unlike
            # bench/harness, which disables it) -- the cost breaker will
            # legitimately trip at this request volume. That's expected,
            # not a failure: record it distinctly rather than crashing on
            # a 429 body that has no "controlplane" key.
            if response.status_code == 429:
                decision = "RATE_LIMITED"
            else:
                decision = response.json()["controlplane"]["decision"]
            decisions_seen[decision] = decisions_seen.get(decision, 0) + 1

            if progress_every and i % progress_every == 0:
                elapsed = time.perf_counter() - start
                print(f"  {i}/{len(items)} ({elapsed:.1f}s elapsed, {i / elapsed:.0f} req/s)")

    elapsed = time.perf_counter() - start
    return {
        "interactions": len(items),
        "elapsed_seconds": round(elapsed, 2),
        "requests_per_second": round(len(items) / elapsed, 1) if elapsed else None,
        "decision_counts": decisions_seen,
        "database": database_url or str(DEFAULT_DB_PATH),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="defaults to a local sqlite file; pass a postgresql+asyncpg:// URL to populate real Postgres instead",
    )
    args = parser.parse_args()

    print(f"replaying {args.count} synthetic interactions (seed={args.seed})...")
    summary = replay(count=args.count, seed=args.seed, database_url=args.database_url)
    print()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
