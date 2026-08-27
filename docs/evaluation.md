# Evaluation

Every number on this page came from an actual script run in this
repository (`CLAUDE.md` rule #2 — never fabricated). Reproduce any of
them yourself:

```bash
python -m bench.harness.run_benchmark          # main benchmark, writes bench/results/benchmark_results.json
python -m bench.harness.run_appetite_sweep     # risk-appetite sweep, writes bench/results/appetite_sweep_results.json
```

Both are deterministic (`--seed 42` default) — rerunning reproduces the
same dataset; the metrics vary only by real, small (~sub-millisecond to
low-millisecond) wall-clock timing noise from the machine they're run on.

## Methodology

`bench/dataset/generate.py` builds 400 synthetic interactions, seeded and
deterministic. Ground truth is correct *by construction* — each item is
generated from a template whose category determines its labels, not
inferred by running a detector over generated text (which would make
precision/recall trivially perfect for whatever detector generated the
labels). Two real bugs were caught and fixed in this generator while
building it (see `tests/unit/test_dataset_generate.py`'s regression
tests): a number-mutation that could be a silent no-op on facts with no
digits, and a mutation that could coincidentally land on another number
already present in the same sentence — both would have mislabeled a
still-true fact as "hallucinated."

Categories and their ground truth:

| Category | `grounded` | `has_pii` | Share |
|---|---|---|---|
| `grounded` | True | False | 25% |
| `grounded_with_pii` | True | True | 10% |
| `hallucinated_contradicted` | False | False | 20% |
| `hallucinated_unverifiable` | False | False | 15% |
| `pii` | False | True | 10% |
| `policy_violation` | — (not scored) | False | 10% |
| `clean_greeting` | — (not scored) | False | 10% |

`grounded` means "this claim's assertion appears in the corpus the claim
verifier actually has access to" (i.e. the *correct* verdict is
`SUPPORTED`) — not "true in the real world." A true statement the toy
corpus can't confirm should correctly verify `UNVERIFIABLE`, and labeling
it `grounded=True` would penalize the detector for honestly admitting it
has no evidence.

**Only hallucination and PII detection get precision/recall** — the only
two risk categories with a real detector behind them
(`bench/metrics/metrics.py`). The dataset's `policy_violation` label is
carried for future use (spec's required ground-truth coverage) but no
metric is computed for it: there's no policy-violation detector to score.

## Benchmark results: ALWAYS_SHALLOW vs ALWAYS_DEEP vs ADAPTIVE

400 interactions, seed 42, run in this environment
(`bench/results/benchmark_results.json`):

| Mode | Tier 1 rate | Escalation rate | p50 latency | p95 latency | Hallucination recall | Hallucination precision | PII recall | PII precision |
|---|---|---|---|---|---|---|---|---|
| ALWAYS_SHALLOW | 0% | 0% | 7.29ms | 9.05ms | 0% | n/a (0 predicted positive) | 0% | n/a |
| ALWAYS_DEEP | 100% | 30.75% | 11.23ms | 14.08ms | 100% | 100% | 100% | 100% |
| ADAPTIVE | 69.5% | 26.25% | 10.80ms | 13.44ms | 99.44% | 100% | 100% | 100% |

This is the safety/cost/latency tradeoff the spec asks for, demonstrated
rather than asserted: ADAPTIVE matches ALWAYS_DEEP's detection quality
(zero false positives in either mode — precision 100% throughout) while
running Tier 1's real analysis work on only 69.5% of traffic instead of
100%, landing between ALWAYS_SHALLOW and ALWAYS_DEEP on latency.

**ADAPTIVE's one missed hallucination** (179/180 vs ALWAYS_DEEP's
180/180) is explained, not just observed: it's a claim asserting a single
low-magnitude number ("...within 2 days...") that scores 0.45 on Tier 0's
`quick_risk_score` — just under `internal_copilot`'s deliberately higher
`tier1_trigger` (0.5, that tenant's configured tolerance for low-signal
content). The adaptive threshold is correctly reflecting the policy it
was configured with; it isn't a detector bug.

## Calibration (Expected Calibration Error)

`bench/metrics/calibration.py` bins the hallucination risk score against
real outcomes from the same benchmark run:

| Mode | ECE | Claims scored |
|---|---|---|
| ALWAYS_SHALLOW | n/a — no claims scored (Tier 1 never ran) | 0 |
| ALWAYS_DEEP | 0.160 | 320 |
| ADAPTIVE | 0.184 | 278 |

An ECE of 0.160–0.184 is real, not fabricated to look good — the
heuristic verifier's scores cluster at a few fixed confidence levels
rather than forming a smooth probability distribution, so this is a
meaningful, explainable gap rather than a rounding artifact. Inspecting
the reliability bins directly (`bench/metrics/calibration.py:reliability_bins`)
shows exactly where it comes from:

| Score bin | Claims | Avg. confidence | Observed hallucination rate |
|---|---|---|---|
| 0.0–0.1 (SUPPORTED) | 140 | 0.00 | 0.0% — perfectly calibrated |
| 0.5–0.6 (UNVERIFIABLE, no evidence found) | 83 | 0.50 | 100% |
| 0.9–1.0 (CONTRADICTED / number-match SUPPORTED) | 97 | 0.90 | 100% |

Almost the entire ECE comes from the 0.5–0.6 bin: `UNVERIFIABLE` claims
get a flat 0.5 score by design — it represents genuine "we don't know,"
not "we're fairly confident it's fake" (`policy/engine.py`'s comment on
this: `UNVERIFIABLE` is never treated as evidence of falsehood). On *this*
dataset, though, every `UNVERIFIABLE` item happens to also be actually
hallucinated (by construction — the dataset's ungrounded categories have
no corpus backing at all), so the honest, deliberately humble 0.5 score
under-states the true positive rate in this particular sample. That's a
property of evaluating an honesty-calibrated score against a dataset
where "no evidence" and "actually false" are highly correlated, not a
flaw in the scoring logic itself.

## Risk appetite sweep: is it actually not cosmetic?

`bench/harness/run_appetite_sweep.py` runs the same 400-item dataset
through the real gateway at five appetite settings, applying
`policy/appetite.py`'s scaling on top of each tenant's real configured
policy (`bench/results/appetite_sweep_results.json`):

| Appetite | Tier 1 rate | Escalation rate | p50 latency | Hallucination recall | Hallucination precision |
|---|---|---|---|---|---|
| 0.1 (permissive) | 20.0% | 2.25% | 8.39ms | 22.2% | 100% |
| 0.3 | 30.25% | 7.0% | 8.95ms | 45.0% | 100% |
| 0.5 (tenant default) | 69.5% | 26.25% | 12.76ms | 99.4% | 100% |
| 0.7 | 69.75% | 26.5% | 12.78ms | 100% | 100% |
| 0.9 (strict) | 69.75% | 26.5% | 12.63ms | 100% | 100% |

Monotonic, real, and measured: recall climbs from 22.2% to 100% as
appetite tightens, escalation rate and Tier 1 invocation climb
alongside it, latency rises with the extra analysis work, and precision
never drops — tightening the gate doesn't manufacture false positives on
this dataset. It plateaus between 0.7 and 0.9 because every item in this
dataset that's catchable at all is already caught by 0.7 — a real
saturation effect, not a bug.

## Human agreement

Computed from real reviews submitted through the console
(`console/backend/main.py:/api/human-agreement/{tenant}`) — not
backfilled, not estimated. With zero reviews submitted it reports
`reviewed_count: 0, agreement_rate: null`, never a fabricated default.
See `docs/demo-scenarios.md`'s Scene 9 for how to generate real review
data and watch the number change live.

## Limitations

- Every benchmark and sweep run here uses a scripted fake provider
  (`bench/harness/run_benchmark.py:HarnessProvider`) — there's no live
  LLM API access in the environment this was built in. Every number
  reflects real, measured behavior of the actual governance pipeline
  against those scripted responses, not real model output variance.
- Cost breaker and model routing are deliberately disabled in both the
  main benchmark and the appetite sweep, to isolate the mechanism each
  script is actually testing (Tier 0/1 depth, and appetite scaling,
  respectively) from Scene 5/6's separate, already-tested mechanisms.
- Latency figures are from this sandboxed environment's hardware — rerun
  the scripts on your own hardware before treating any latency number
  here as representative of a production deployment.
- See `docs/assumptions.md` for the full list of what's a documented
  simplification versus what's fully implemented.
