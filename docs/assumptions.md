# Assumptions and Known Limitations

Every simplification below is deliberate and was made under a real
constraint (this is a prototype, not a production deployment; there's no
live LLM API access in the environment this was built in; certain
mechanisms need real usage data to build responsibly). Each one is also
implemented honestly: the schema/interface anticipates the real version,
and nothing pretends to be more complete than it is. `docs/roadmap.md` has
the phase-by-phase version of this list with the reasoning attached to
where each item was introduced; this page is the consolidated reference.

## Detectors are heuristic, not ML models

- **Claim verification** (`detectors/hallucination/claim_verifier.py`) is
  a deterministic keyword+number-overlap heuristic against a small
  (5-document) fake corpus, not a real NLI cross-encoder. It produces
  correct SUPPORTED/CONTRADICTED/UNVERIFIABLE behavior on the demo
  scenarios and the benchmark dataset (100% precision, 99.4–100% recall
  — see `docs/evaluation.md`), but won't generalize to arbitrary
  real-world text the way a real entailment model would.
- **PII detection** (`detectors/pii/regex_pii.py`) is regex-based
  (phone/email/credit_card/government_id/bank_account patterns), not
  Presidio. No free-form named-entity recognition — it won't catch a
  name or address as PII, only pattern-matchable identifiers.
- **Prompt-injection detection** (`detectors/injection.py`) is a fixed
  set of ~7 regex patterns for common instruction-override phrasing, not
  a claim of complete jailbreak coverage. It demonstrates the mechanism
  (untrusted content gets scanned and neutralized before the model sees
  it), not exhaustive adversarial robustness.
- **`toxicity`, `policy`, `bias` risk labels** exist in
  `detectors/base.py:RiskVector`'s schema (spec §5 requires the
  categories be represented) but have no detector behind them —
  `evaluated=False` on every claim, which the console and the benchmark
  harness both treat as "not run," never as "confirmed clean."

## Taint matching is numeric-value-only

`ledger/taint.py` catches a number reused verbatim or reformatted (₹48,000
↔ 48000) across conversation turns. It does not catch:

- A value **derived through arithmetic** from a tainted one (e.g. "half of
  the ₹48,000" as a new, differently-valued tool-call argument).
- **Non-numeric tainted facts** used as justification for an action (e.g.
  a fabricated policy clause cited as the reason a refund should be
  issued, where the tool-call argument itself isn't the tainted value).

`policy.tool_calls.require_verified_provenance` exists in the schema for
a broader "every consequential argument needs a SUPPORTED source" check,
but only the exact-taint-match gate is implemented.

## Policy fields present in the schema, not yet enforced

- `latency_budget_ms` is informational — nothing currently cuts off a
  request early for exceeding it.
- `risk_thresholds.block_trigger` is validated (must be `>= tier2_trigger`)
  but nothing in `policy/engine.py` currently reads it — the only paths
  to a whole-response BLOCK today are a hard-block PII category or a
  tenant's `unverifiable_handling: BLOCK` setting.
- `escalation.max_escalation_rate` is a target, not an enforced cap —
  nothing currently throttles escalations once a tenant exceeds it.

## Infrastructure simplifications

- **Audit chain concurrency**: `ledger/audit.py` reads the latest hash and
  inserts the next row without a database-level lock — correct for this
  prototype's effectively-serial demo/eval workloads, not for concurrent
  production writers (would need `SELECT ... FOR UPDATE` or a
  single-writer queue).
- **Cost breaker**: in-memory and per-process
  (`gateway/middleware/cost_breaker.py`), not Redis-backed — a
  multi-replica deployment would need shared state to enforce one limit
  across instances. Token counts are a `chars/4` proxy, not a real
  tokenizer count (an internal rate-limit heuristic, never a number
  reported in a benchmark).
- **Risk appetite lookup**: queried fresh from Postgres on every gateway
  request (`gateway/routes/chat.py:_effective_policy`), not cached —
  correct-over-fast, acceptable at this prototype's request volume, would
  want caching with invalidation at real scale.

## Evaluation gaps, not fabricated to fill them

- **No metric for `policy_violation`**: the benchmark dataset
  (`bench/dataset/generate.py`) carries this ground-truth label (spec's
  required coverage), but no policy-violation detector exists, so no
  precision/recall is reported for it — see `docs/evaluation.md`.
- **Human agreement** is now real (Phase 5 added the review mechanism,
  `console/backend/main.py:/api/human-agreement`), but only reflects
  whatever reviews have actually been submitted through the console —
  it's not backfilled or estimated for decisions nobody reviewed.
- **Recalibration is a suggestion, not an auto-apply**
  (`policy/recalibration.py`): silently adjusting a live safety threshold
  from a small, possibly-biased sample of human reviews with nobody
  confirming the change would itself be an unaudited, unsupervised way
  to alter governance behavior. A human still has to apply the suggestion
  through the same audited risk-appetite control.
- **Recalibration only detects "too aggressive"**: it works from reviews
  of ESCALATE/BLOCK decisions (the ones with review friction), so it has
  no signal about hallucinations/PII that were silently allowed and never
  flagged for review in the first place.
- **Tier 2** ("deep verification," spec §10's third scrutiny tier) isn't
  implemented — Tier 1's heuristic detectors are the deepest analysis
  currently available.

## No real upstream LLM in this environment

Every test, benchmark run, and replayer run in this repository uses a
scripted fake provider (`gateway/providers/base.py:Provider` implementations
built for tests) — there is no live API key or network access to a real
LLM in the environment this was built in. `gateway/providers/openai_compatible.py`
is real, working code for the real integration; it's just never been
exercised against an actual upstream API in this session. Every number in
`docs/evaluation.md` and `docs/roadmap.md` comes from running the real
governance pipeline against these scripted responses — real measured
system behavior, just not real model outputs.
