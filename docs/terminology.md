# Terminology

## Claims and verification

**Claim** — one atomic factual assertion extracted from a response
(`detectors/claims.py`). Span-tracked so remediation can edit just that
sentence, not the whole response. Questions and short greetings aren't
extracted as claims — they don't assert anything checkable.

**Verdict** — the outcome of checking a claim against evidence
(`detectors/base.py:Verdict`). Exactly three values, and they are **not**
interchangeable:

- `SUPPORTED` — the claim matches something in the evidence available.
- `CONTRADICTED` — the claim conflicts with the evidence available.
- `UNVERIFIABLE` — there isn't enough evidence to say either way.

**`UNVERIFIABLE` is not `FALSE`.** This is the project's first
non-negotiable invariant (`CLAUDE.md` rule #3). A claim ControlPlane has
no evidence for is not the same as a claim ControlPlane has evidence
*against* — collapsing the two would mean confidently calling something
false when the honest answer is "we don't know," which is its own kind of
misinformation. Policy decides what to *do* about `UNVERIFIABLE` (allow,
hedge, escalate, block — `policy.unverifiable_handling`), but the verdict
itself never gets rewritten to `CONTRADICTED` to make that decision easier.

**Risk vector** — a claim's assessment across independent, non-exclusive
categories (`detectors/base.py:RiskVector`): `hallucination`, `pii`,
`policy`, `toxicity`, `bias`. A single claim can be both
`hallucination=true` and `pii=true` at once (e.g. an invented phone
number). Each category's `RiskFinding` carries `detected`, `score`
(risk magnitude — 0 for a confirmed-safe claim, not "confidence in
whichever verdict came back," see `policy/engine.py`), and `evaluated`
(whether a real detector ran at all — `toxicity`/`policy`/`bias` are
`evaluated=False` in this prototype: present in the schema, no detector
behind them yet, never silently reported as "clean").

## Provenance and taint

**Provenance** — where a claim's evidence came from
(`detectors/base.py:Provenance`): `source` (`retrieved_doc`,
`model_prior`, or `user_input`), `source_id` (which document, if any),
the `verdict` it produced, and which conversation `turn_id` it happened
in.

**Taint** — a claim is tainted when its verdict isn't `SUPPORTED`
(`policy/engine.py` sets `Claim.taint_status`). Taint is what
**propagates**: `ledger/taint.py` checks whether a later turn's tool-call
argument traces back to a tainted claim earlier in the same conversation
(matched by the underlying numeric value, independent of formatting —
₹48,000 and 48000 are the same tainted number). A tainted argument to a
consequential tool call is blocked or escalated before the call ever
reaches the application — see Scene 7 in `docs/demo-scenarios.md`.

## Remediation and decisions

**Remediation** — the action taken on one claim (`policy.models.Remediation`):
`ALLOW`, `HEDGE`, `REDACT`, `REMOVE`, `ADD_CITATION`, `ESCALATE`, `BLOCK`.
Chosen per-claim by the policy engine, never response-wide by default —
**surgical remediation** means one bad sentence gets fixed, the rest of
the response survives.

**Decision** — the response-level rollup (`policy.engine.Decision`):
`ALLOW`, `MODIFY`, `ESCALATE`, `BLOCK`. Computed as the most severe
remediation across all claims and gated tool calls in the response — a
single hard-block PII category is the one thing that legitimately
produces a whole-response `BLOCK` from a single claim; everything else
composes.

## Scrutiny tiers

**Tier 0** — a cheap, regex-only gate (`detectors/tier0.py`) deciding
whether a response needs full analysis at all. Configurable per tenant
via `risk_thresholds.tier1_trigger`.

**Tier 1** — the full pipeline: claim extraction, claim verification, PII
detection, risk vector, remediation. Runs when Tier 0's score clears the
tenant's threshold.

**Tier 2** — not implemented. The spec's three-tier cascade includes a
"deep verification" tier beyond Tier 1; this prototype's Tier 1 heuristic
detectors are the deepest analysis currently available. Documented in
`docs/roadmap.md`, not silently assumed.

## Risk appetite and calibration

**Risk appetite** (`policy/appetite.py`) — a single per-tenant scalar in
`[0.0, 1.0]` (0.5 = the tenant's own configured thresholds, unchanged)
that scales `risk_thresholds` up or down. Demonstrated to move real
detection recall/precision, escalation rate, and latency on the labeled
benchmark dataset (`bench/harness/run_appetite_sweep.py`), not a cosmetic
slider.

**Expected Calibration Error (ECE)** (`bench/metrics/calibration.py`) —
how well a risk score's magnitude matches observed outcomes: does a
0.9-scored claim actually turn out to be risky ~90% of the time? Computed
from real (score, outcome) pairs collected during an actual benchmark
run, never asserted.

## Cost and traffic tooling

**Cost circuit breaker** (`gateway/middleware/cost_breaker.py`) — a
per-tenant sliding-window limit on request count and estimated token
volume, checked before the upstream provider is ever called.

**Model routing** — cheap-model-first request handling
(`policy.model_routing`): the cheap model is tried first and validated by
the governance engine; only a flagged response triggers a retry against a
stronger model.

**Benchmark harness** (`bench/harness/`) vs. **traffic replayer**
(`demo/replayer/`) — the harness runs a small labeled dataset to measure
*accuracy* (precision/recall/calibration); the replayer runs a large
unlabeled synthetic volume to populate the console with realistic traffic
and measure throughput/latency at scale. Different tools, different jobs.
