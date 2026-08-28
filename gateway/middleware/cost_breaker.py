"""In-memory sliding-window cost/retry circuit breaker (spec §17, Scene 5:
retry storm / token spike).

Per-tenant: tracks request timestamps and estimated token counts over a
trailing window (policy.cost_breaker.window_seconds) and trips -- rejects
further requests without ever calling the upstream provider -- once either
the request-count or token limit is exceeded within that window.

Known simplification: in-memory and per-process, not Redis-backed. Correct
for this prototype's single-instance demo/eval workloads; a multi-replica
deployment would need shared state (Redis, per spec's suggested stack) to
enforce one limit across instances. Documented in docs/roadmap.md.

Token counts are a cheap proxy (chars / 4), not a real tokenizer count --
sufficient to trip a breaker on a genuine spike. This is purely an
internal rate-limit heuristic, not a number reported in any benchmark, so
it doesn't fall under the project's "never fabricate a number" rule the
way an evaluation/latency metric would.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from policy.models import CostBreakerPolicy


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class CostBreaker:
    def __init__(self):
        self._windows: dict[str, deque[tuple[float, int]]] = defaultdict(deque)

    def check_and_record(self, tenant_id: str, tokens: int, policy: CostBreakerPolicy) -> bool:
        """Returns True and records the request if it's within budget;
        returns False (and records nothing) if the breaker is tripped."""
        if not policy.enabled:
            return True

        now = time.monotonic()
        window = self._windows[tenant_id]
        cutoff = now - policy.window_seconds
        while window and window[0][0] < cutoff:
            window.popleft()

        request_count = len(window)
        token_total = sum(t for _, t in window)

        if (
            request_count >= policy.max_requests_per_window
            or token_total + tokens > policy.max_tokens_per_window
        ):
            return False

        window.append((now, tokens))
        return True
