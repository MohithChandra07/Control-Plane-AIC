# Roadmap

Tracks phase status honestly — update this file when a phase's definition
of done is actually met, not before.

## Phase 1 — Foundation ✅ done

- [x] Repo structure (`gateway/`, `policy/`, `ledger/`, `configs/`, `tests/`)
- [x] Policy schema (`policy/models.py`) + loader (`policy/loader.py`)
- [x] Three tenant configs (`configs/customer_support.yaml`,
      `internal_copilot.yaml`, `regulated_agent.yaml`)
- [x] FastAPI gateway with OpenAI-compatible `/v1/chat/completions`
- [x] Provider abstraction (`gateway/providers/`) — one OpenAI-compatible
      provider implementation
- [x] Postgres-backed, hash-chained audit ledger (`ledger/`)
- [x] Tests: policy loader, audit chain (incl. tamper detection), gateway
      round trip (clean / unknown tenant / upstream failure / per-tenant)

**Definition of done (spec §23):** a real client can communicate through
the ControlPlane gateway and a decision is recorded. Met — see
`tests/integration/test_gateway_roundtrip.py`.

**Known simplification:** the audit chain has no database-level lock
around "read latest hash, then insert" (see `ledger/audit.py` docstring) —
fine for this prototype's effectively-serial demo/eval workloads, not for
concurrent production writers.

## Phase 2 — Basic Governance ✅ done

- [x] Tier 0/Tier 1 adaptive scrutiny gate (`detectors/tier0.py`,
      `policy/engine.py`) — configurable per-tenant `tier1_trigger`, not a
      vague "if it feels risky" check
- [x] Claim extraction (`detectors/claims.py`) — span-tracked sentence
      segmentation, skips questions/greetings
- [x] Claim verification (`detectors/hallucination/`) — SUPPORTED /
      CONTRADICTED / UNVERIFIABLE against a small fake corpus
      (`data/corpus/`)
- [x] PII detection (`detectors/pii/regex_pii.py`)
- [x] Multi-label risk vector (`detectors/base.py:RiskVector`) — a claim
      can be hallucination=true and pii=true at once
- [x] Policy engine / surgical remediation (`policy/engine.py`) —
      per-claim remediation (ALLOW/HEDGE/REDACT/REMOVE/ADD_CITATION/
      ESCALATE/BLOCK), only hard-block PII blocks the whole response
- [x] Wired into the gateway with per-claim audit rows
      (`gateway/routes/chat.py`)
- [x] Tests: 39 passing (12 unit modules covering claims/PII/verifier/
      engine + 3 gateway integration tests exercising Scenes 1–3 end to
      end through the real pipeline)

**Definition of done (spec §23):** Scenes 1–3 work end-to-end. Met — see
`tests/integration/test_gateway_governance.py`.

**Known simplifications** (documented, not hidden):
- Claim verification is a deterministic keyword+number-overlap heuristic
  against a 2-document fake corpus, not a real NLI cross-encoder model.
  It gives correct SUPPORTED/CONTRADICTED/UNVERIFIABLE behavior on the
  demo scenarios but won't generalize the way a real entailment model
  would.
- PII detection is regex-based (phone/email/credit_card/government_id/
  bank_account), not Presidio — no free-form NER (names, addresses).
- toxicity/policy/bias risk labels are present in the schema
  (`RiskVector`) but have no detector behind them yet; their
  `evaluated=False` marks them as "not run", not "clean".
- `taint_status` on claims is always `None` in Phase 2 — taint
  propagation is Phase 3 scope.
- Tier 0 buys little real latency today since Tier 1 is itself
  regex/heuristic-based rather than a real model call; the gating
  *mechanism* is real and will start mattering once Phase 4/5 swaps in
  real detectors.

## Phase 3 — Agent Safety ✅ done

- [x] Provenance carries `turn_id` now (`turn_id` = count of user-role
      messages in the request, computed statelessly per request since the
      client resends full history each call — no session store needed)
- [x] Taint propagation across turns (`ledger/taint.py`) — a claim is
      tainted when its verdict isn't SUPPORTED (`policy/engine.py`
      activates `Claim.taint_status`); a later turn's tool-call argument
      is checked against every tainted claim in the same
      `conversation_id`, matched on the underlying number regardless of
      formatting (₹48,000 vs 48000). No second, unaudited taint store —
      it queries the same hash-chained `audit_events` table (added a
      `claim_text` column so there's something to match against)
- [x] Tool-call interception + sink classification
      (`data/tools.yaml` + `policy/tools.py`) + action gating
      (`policy/tool_gate.py`), wired into `gateway/routes/chat.py`:
      every `tool_calls` entry in the response is gated before it reaches
      the application; a BLOCKed (or, under fail-closed, ESCALATEd) call
      is stripped from the response entirely
- [x] Cost circuit breaker (`gateway/middleware/cost_breaker.py`) —
      per-tenant sliding window on request count + estimated tokens,
      checked *before* the upstream provider is ever called
- [x] Cheap-model reroute validated by the checker
      (`policy.model_routing`, wired in `gateway/routes/chat.py`) — cheap
      model tried first, governance engine validates it, only a flagged
      response triggers a retry against the stronger model
- [x] Tests: 61 passing total (5 new integration tests for Scenes 5–7,
      including the critical tainted-refund block, plus unit tests for
      `ledger/taint.py`, `policy/tool_gate.py`, and the cost breaker)

**Definition of done (spec §23):** Scenes 5–7 work end-to-end. Met — see
`tests/integration/test_gateway_scenes_5_7.py`.
`test_scene7_tainted_refund_amount_blocks_tool_call` is the critical one:
turn 1 makes an unverifiable claim about a refund amount, turn 2's
`issue_refund` tool call using that same amount is blocked and never
reaches the application; `test_scene7_untainted_refund_amount_is_allowed`
proves the gate isn't just blocking `issue_refund` outright.

**Known simplifications** (documented, not hidden):
- Taint matching is numeric-value-only (spec's own example is numeric):
  it catches the same number reused verbatim or reformatted, not a value
  derived through arithmetic from a tainted one, and not non-numeric
  tainted facts (e.g. a fabricated policy clause used as justification
  for an action). See `ledger/taint.py`.
- `ToolCallPolicy.require_verified_provenance` exists in the schema but
  isn't separately enforced yet — Phase 3 only implements the exact-taint
  -match gate, not a broader "every consequential argument needs a
  SUPPORTED source" check.
- The cost breaker is in-memory and per-process, not Redis-backed —
  correct for this prototype's single-instance demo, not for multiple
  gateway replicas sharing one limit. Token counts are a cheap `chars/4`
  proxy, not a real tokenizer count (this is an internal rate-limit
  heuristic, not a number that goes in any benchmark/eval report).
- Model routing always tries the cheap model first when enabled; there's
  no logic yet for routing some requests straight to the strong model
  based on request shape (that's closer to Phase 4/5 territory once
  there's real cost/latency data to tune it against).

## Phase 4 — Observability + Evaluation ✅ done

- [x] Synthetic labeled dataset generator (`bench/dataset/generate.py`) —
      400 deterministic interactions (seed=42) covering grounded vs
      hallucinated, PII vs clean, and policy-violation vs clean (the last
      one labeled for future use; see below). Ground truth is correct by
      construction, not run through the detector under test to derive it
      (that would make precision/recall trivially perfect)
- [x] Benchmark harness (`bench/harness/run_benchmark.py`) — one command
      (`python -m bench.harness.run_benchmark`) runs the dataset through
      the real gateway under ALWAYS_SHALLOW / ALWAYS_DEEP / ADAPTIVE
      scrutiny configs and reports real, measured metrics
- [x] Traffic replayer (`demo/replayer/replay.py`) — one command
      (`python -m demo.replayer.replay --count 10000`) posts synthetic
      traffic through the real gateway to populate the audit ledger;
      measured 10,000 interactions in 99.9s (~100 req/s) against a local
      SQLite file in this environment
- [x] Console backend (`console/backend/main.py`) — small, separate,
      read-only FastAPI service over the same `audit_events` table
      (`/api/summary`, `/api/events`, `/api/events/{request_id}`)
- [x] Console frontend (`console/frontend/`) — Vite + React dashboard:
      summary cards, a decision breakdown, a paginated recent-requests
      table, tenant filter, and a per-request drill-down drawer showing
      claims (verdict, risk labels, taint status, remediation) and gated
      tool calls. Verified rendering against real replayed data via a
      headless-browser screenshot in this session (not just "it builds")
- [x] Explicit `kind` discriminator added to `audit_events`
      (`ledger/models.py`) — "request" / "claim" / "tool_call" rows were
      previously only distinguishable by which JSON fields happened to be
      set, which broke once tool-call rows and model-routing rows both
      started populating `action`; the console backend needed a reliable
      way to tell them apart
- [x] Tests: 93 passing total (dataset generator, bench metrics, harness
      smoke tests, replayer smoke test, console backend integration tests)

**Definition of done (spec §23):** dashboards are live (console reads
real data, verified visually) and the benchmark runs from one command.
Met.

**Real measured results** (`bench/results/benchmark_results.json`, 400
interactions, seed=42 — reproduce with `python -m bench.harness.run_benchmark`):

| mode | Tier 1 rate | escalation rate | p50 latency | p95 latency | hallucination recall | PII recall |
|---|---|---|---|---|---|---|
| ALWAYS_SHALLOW | 0% | 0% | 6.7 ms | 8.6 ms | 0% | 0% |
| ALWAYS_DEEP | 100% | 30.75% | 10.7 ms | 13.1 ms | 100% | 100% |
| ADAPTIVE | 69.5% | 26.25% | 10.7 ms | 13.8 ms | 99.44% | 100% |

Precision was 1.0 (zero false positives) for both detectors in every
config that ran Tier 1 — this heuristic detector doesn't cry wolf on this
dataset, though see Phase 2/3's documented limitations on how far the
heuristic generalizes beyond it. ADAPTIVE's one missed hallucination
(vs. ALWAYS_DEEP's zero) is explained, not just observed: it's a
single-digit claim ("...within 2 days...") that scores just under
`internal_copilot`'s deliberately higher `tier1_trigger` (0.5, that
tenant's configured tolerance) — the adaptive threshold correctly
reflects the policy it was configured with, not a detector bug. Latency
figures are from this sandboxed environment's hardware, not a
production benchmark environment; rerun `bench/harness/run_benchmark.py`
to get numbers for your own hardware.

**Known simplifications** (documented, not hidden):
- No metric is computed for `policy_violation` — the dataset carries the
  label (spec's required ground-truth coverage), but no policy-violation
  detector exists yet. See `bench/metrics/metrics.py`.
- "Human agreement" and Expected Calibration Error aren't computed here —
  no human-labeled review data exists in this environment, and ECE is
  Phase 5 scope.
- All three benchmark configs disable the cost breaker and model routing
  so the comparison isolates the Tier 0/1 scrutiny-depth tradeoff
  specifically; the cheap-model-reroute cost story is Scene 6's job
  (tested separately in Phase 3), not this harness's.
- The traffic replayer also disables the cost breaker, for the same
  reason it isn't the point of that tool — Scene 5's own test already
  proves the breaker trips under realistic-paced traffic; running it
  enabled here would just starve the dashboard of governance data by
  filling it with 429s at replay speed.
- The replayer defaults to a local SQLite file for a turnkey run; pass
  `--database-url postgresql+asyncpg://...` to point it at a real
  Postgres instance instead.
- The console frontend has one known moderate `npm audit` advisory
  (esbuild's dev-server-only CORS issue, fixed only by a breaking Vite
  major-version bump) — not applied since it doesn't affect the
  production build and this is local dev tooling for a prototype, not an
  internet-facing service.

## Phase 5 — Calibration + Demo Hardening ✅ done

- [x] Expected Calibration Error (`bench/metrics/calibration.py`) —
      `reliability_bins()` + `expected_calibration_error()` computed from
      real (score, outcome) pairs out of an actual benchmark run, not
      simulated
- [x] Risk appetite control (`policy/appetite.py`) — `apply_risk_appetite()`
      scales a tenant's own `risk_thresholds` proportionally around a
      0.5=no-change baseline (relaxes toward 1.0 below 0.5, tightens
      toward 0.0 above it), preserving each tenant's relative strictness;
      set live via the console (`PUT /api/risk-appetite/{tenant}`,
      persisted in a new `TenantSetting` table) and read fresh on every
      gateway request (`gateway/routes/chat.py:_effective_policy`) — no
      restart needed
- [x] Human override + feedback loop (`console/backend/main.py`) —
      `POST /api/reviews` looks up the real target row by request/claim
      id (never trusts a client-asserted decision), audits every review
      as its own hash-chained `kind=human_review` row;
      `GET /api/human-agreement/{tenant}` computes a real agreement rate;
      `policy/recalibration.py:suggest_recalibration()` surfaces a
      risk-appetite-relaxation *suggestion* once ESCALATE/BLOCK
      disagreement crosses a threshold — never auto-applies it, a human
      still has to apply it through the audited appetite control
- [x] Prompt-injection detection on untrusted input (`detectors/injection.py`,
      Scene 4) — scans only `role="tool"`/`"function"` messages (never
      `role="user"`) for ~7 instruction-override patterns, neutralizes
      matched spans with `[REDACTED_INJECTION_ATTEMPT]` *before* the
      request is forwarded upstream
- [x] Console frontend: `RiskAppetiteControl.tsx` (slider, commits on
      release) and `HumanFeedbackPanel.tsx` (agreement rate +
      recalibration suggestion banner); `EventDetailDrawer.tsx` grew
      per-claim and overall-decision Agree/Disagree review controls
- [x] Appetite sweep harness (`bench/harness/run_appetite_sweep.py`) —
      runs the same 400-item dataset at five appetite settings to prove
      the mechanism is real, not cosmetic
- [x] Full documentation set (`docs/`) — `project-brief.md`,
      `terminology.md`, `policies.md`, `assumptions.md`, `architecture.md`
      (with Mermaid diagrams), `demo-scenarios.md` (all 9 scenes,
      reproducible by exact test name), `evaluation.md` (every number
      re-measured and transcribed from an actual script run before being
      written down)
- [x] Tests: 145 passing total (Phase 5 added unit tests for appetite,
      recalibration, calibration, and injection detection, plus
      integration tests for the appetite-gated gateway path, the appetite
      sweep, human review end to end, Scene 4 injection, and Scene 8
      tenant differentiation)

**Definition of done (spec §23):** all 9 demo scenes work end-to-end and
are individually reproducible, calibration is measured (not asserted),
risk appetite visibly changes gateway behavior, and a human review loop
produces an auditable, non-silent recalibration suggestion. Met.

**Real measured results** (400 interactions, seed=42 — reproduce with
`python -m bench.harness.run_benchmark` and
`python -m bench.harness.run_appetite_sweep`; full detail and reliability
bins in `docs/evaluation.md`):

| mode | Tier 1 rate | escalation rate | p50 latency | hallucination recall | ECE (n scored) |
|---|---|---|---|---|---|
| ALWAYS_SHALLOW | 0% | 0% | 7.29 ms | 0% | n/a (0) |
| ALWAYS_DEEP | 100% | 30.75% | 11.23 ms | 100% | 0.160 (320) |
| ADAPTIVE | 69.5% | 26.25% | 10.80 ms | 99.44% | 0.184 (278) |

Appetite sweep (same dataset, `regulated_agent`-style thresholds scaled
per tenant): hallucination recall climbs monotonically from 22.2% at
appetite 0.1 to 100% at appetite 0.7, with precision holding at 100%
throughout and Tier 1/escalation rate rising alongside it — real,
measured evidence the appetite control changes actual gateway behavior,
not just a config value nobody reads. It plateaus between 0.7 and 0.9
because every catchable item in this dataset is already caught by 0.7.

**Known simplifications** (documented, not hidden — full list in
`docs/assumptions.md`):
- `unverifiable_handling`-style detectors remain heuristic, not ML —
  ECE of 0.160–0.184 is real and explained (traced to the flat, honestly
  humble 0.5 score for `UNVERIFIABLE`), not a rounding artifact.
- Recalibration only detects "too aggressive" (from ESCALATE/BLOCK review
  disagreement) — it has no signal about hallucinations/PII that were
  silently allowed and never flagged for review.
- Human agreement is real but not backfilled — it only reflects whatever
  reviews have actually been submitted through the console.
- Injection detection is ~7 fixed regex patterns demonstrating the
  mechanism, not a claim of exhaustive jailbreak coverage.
- Tier 2 deep verification still isn't implemented — Tier 1's heuristic
  detectors remain the deepest scrutiny available.
- `latency_budget_ms`, `risk_thresholds.block_trigger`, and
  `escalation.max_escalation_rate` are present in the policy schema but
  still not separately enforced (unchanged from earlier phases).
