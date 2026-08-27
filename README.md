# ControlPlane

ControlPlane is an AI governance and safety gateway: it sits between an
application and an AI model/agent, inspects what goes in and comes out, and
lets policy — not silent model behavior — decide whether a response or a
tool call is allowed, modified, escalated, or blocked.

```
Application → ControlPlane Gateway → AI Model → ControlPlane Analysis → Policy Engine → ALLOW / MODIFY / ESCALATE / BLOCK → Application
```

For agents, ControlPlane also intercepts consequential tool calls so an
unverified or tainted claim (e.g. a hallucinated refund amount) can never
silently become a real-world action — this is implemented end to end,
see Scene 7 in `docs/roadmap.md`.

## Status: Phase 5 (Calibration + Demo Hardening) — all phases done

This repository was built incrementally, phase by phase (see
`docs/roadmap.md`). **Phases 1–5 are done.** Concretely, right now:

- A real client can send an OpenAI-style chat request through the
  ControlPlane gateway, have it forwarded to an upstream OpenAI-compatible
  provider, and get a governed response back.
- Responses go through adaptive scrutiny (Tier 0 cheap gate → Tier 1 full
  pipeline): claim extraction, claim verification against a small fake
  corpus (SUPPORTED/CONTRADICTED/UNVERIFIABLE — UNVERIFIABLE is never
  treated as false), PII detection, and a multi-label risk vector where a
  single claim can be e.g. both `hallucination` and `pii` at once.
- The policy engine applies **surgical remediation** per claim (hedge,
  redact, remove, cite, escalate) rather than blocking a whole response
  for one bad sentence — full-response BLOCK is reserved for deliberate
  cases like a hard-block PII category.
- A claim ControlPlane can't confirm is **tainted**, and that taint
  **propagates across conversation turns**: if a later turn's tool call
  (e.g. `issue_refund(amount=48000)`) uses a value that traces back to an
  unverified/contradicted claim earlier in the same conversation, the
  call is blocked before it ever reaches the application.
- A **cost circuit breaker** trips per tenant on request-count or
  token-volume spikes, short-circuiting before the upstream provider is
  ever called. A **cheap-model-first** routing option calls a cheaper
  model, validates its response with the same governance engine, and
  only retries against a stronger model when the checker flags a problem.
- Every request produces a hash-chained audit ledger entry, plus one
  entry per claim and one per gated tool call.
- Three tenant policies (`configs/*.yaml`) drive different outcomes for
  the same input.
- A **benchmark harness** (`bench/`) runs a 400-item labeled synthetic
  dataset through the real gateway under three scrutiny configurations
  and reports real, measured precision/recall/latency numbers — see
  `docs/roadmap.md` for the actual results from the last run.
- A **traffic replayer** (`demo/replayer/`) populates the audit ledger
  with synthetic traffic (measured: 10,000 interactions in ~100s in this
  environment) so the **console** — a small read-write API
  (`console/backend/`) plus a React dashboard (`console/frontend/`) — has
  real data to show: decision breakdown, latency, a recent-requests
  table, a per-request drill-down into claims and tool-call decisions,
  a live risk-appetite slider, and human review (Agree/Disagree) controls.
- **Expected Calibration Error** (`bench/metrics/calibration.py`) is
  computed from real (score, outcome) pairs out of an actual benchmark
  run, and a **risk-appetite control** (`policy/appetite.py`) lets a
  tenant's caution be dialed up or down live, without a restart or a YAML
  edit — both measured effects are in `docs/evaluation.md`.
- A **human review + recalibration loop**: reviewers can mark a gateway
  decision Agree/Disagree from the console; once disagreement on
  ESCALATE/BLOCK decisions crosses a threshold, `policy/recalibration.py`
  *suggests* (never silently applies) a risk-appetite adjustment.
- **Prompt-injection detection** (`detectors/injection.py`) scans
  untrusted (`role="tool"`/`"function"`) messages for instruction-override
  phrasing and neutralizes matches before the request ever reaches the
  upstream model — a user's own `role="user"` message is never scanned
  this way.

**Known simplifications** (see `docs/assumptions.md` for the full list):
claim verification is a deterministic heuristic, not a real NLI model; PII
detection is regex-based, not Presidio; taint matching is numeric-value
only; the cost breaker is in-memory/per-process, not Redis-backed;
toxicity/policy/bias risk labels exist in the schema but have no detector
behind them yet; no metric is computed for `policy_violation` (labeled in
the dataset, no detector exists); human agreement is real but not
backfilled; recalibration is a suggestion, never an auto-apply; Tier 2
deep verification isn't implemented.

For the full documentation set — architecture diagrams, terminology,
per-tenant policy breakdown, all 9 demo scenes with exact reproduce
commands, and every measured evaluation number — see `docs/`.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env   # fill in UPSTREAM_API_KEY, etc.
docker compose up -d postgres

uvicorn gateway.main:app --reload
```

Then point any OpenAI client at `http://localhost:8000/v1` instead of the
real provider's base URL — the request is forwarded, governed, and
audited. The response carries a `controlplane` extension field with the
decision, scrutiny tier, per-claim verdicts/risk labels/remediations, and
any tool-call gating decisions.

Select a tenant policy with the `X-ControlPlane-Tenant` header (one of
`customer_support`, `internal_copilot`, `regulated_agent`); it defaults to
`DEFAULT_TENANT` from `.env` otherwise. Multi-turn taint tracking needs a
stable `conversation_id`, passed via the request body's `controlplane`
extension object: `{"controlplane": {"conversation_id": "..."}}`.

## Configuration

Tenant policies live in `configs/*.yaml` and are loaded through
`policy/loader.py` into the `policy.models.Policy` schema. The shared tool
sink catalog (which tool names map to which consequence category, e.g.
`issue_refund` → `money_movement`) lives in `data/tools.yaml`, loaded via
`policy/tools.py` — see those files for what each field means.

## Running tests

```bash
pytest
```

145 tests cover policy loading/validation, the hash-chained audit ledger
(including tamper detection), claim extraction, PII detection, the
heuristic claim verifier, the governance engine's remediation logic,
taint lookup across conversation turns, tool-call gating, the cost
breaker, prompt-injection detection, risk appetite scaling, recalibration
suggestions, calibration/ECE metrics, the benchmark dataset generator and
harness, the traffic replayer, the console backend API (including
human review), and the gateway round trip including all 9 demo scenes
end to end — see `tests/unit/` and `tests/integration/`, and
`docs/demo-scenarios.md` for which test proves which scene.

## Running the benchmark

```bash
python -m bench.harness.run_benchmark
```

Runs the 400-item labeled synthetic dataset (`bench/dataset/generate.py`)
through the real gateway under three scrutiny configurations
(ALWAYS_SHALLOW / ALWAYS_DEEP / ADAPTIVE) and writes real, measured
results to `bench/results/benchmark_results.json`. See `docs/roadmap.md`
for the actual numbers from the last run in this repo, and why cost
isn't reported as a dollar figure in this particular harness.

## Populating the console with traffic

```bash
python -m demo.replayer.replay --count 10000
```

Posts synthetic interactions through the real gateway to a local SQLite
file (`demo/replayer/traffic.db` by default; pass `--database-url` to
target real Postgres instead), so the console has real data to show.

## Running the console

```bash
# Terminal 1 — read-only API over the audit ledger
DATABASE_URL="sqlite+aiosqlite:///$(pwd)/demo/replayer/traffic.db" \
  uvicorn console.backend.main:app --port 8001

# Terminal 2 — dashboard
cd console/frontend && npm install && npm run dev
```

Open the printed `http://localhost:5173/` URL. The dashboard auto-refreshes
every 5 seconds and reads only from the audit ledger — nothing on it is
hard-coded demo data.

Select a tenant to see (and set) its live **risk appetite** slider and its
**human review** panel. Click a request row to open its drill-down
drawer, then click Agree/Disagree on any claim or on the overall decision
— `GET /api/human-agreement/{tenant}` and, once enough disagreement
accumulates, `GET /api/recalibration/{tenant}`'s suggestion banner update
immediately, no reload. See `docs/demo-scenarios.md` Scene 9.
