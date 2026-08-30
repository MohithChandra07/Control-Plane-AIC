/**
 * Every number this site renders, with the artefact it was read from.
 *
 * CLAUDE.md rule #2: no benchmark/latency/eval figure appears anywhere in
 * this repo unless a real script produced it. Nothing here is invented for
 * the visual — each entry carries a `source` string that names the file (and
 * the row inside it) the value was transcribed from, and the UI surfaces
 * that source in a tooltip so a judge can go check it.
 *
 * Sources:
 *   bench/results/benchmark_results.json  — `python -m bench.harness.run_benchmark`
 *   bench/results/appetite_sweep_results.json — `python -m bench.harness.run_appetite_sweep`
 *   test suite total — `pytest -q`, 150 passed
 */

export interface Metric {
  label: string;
  value: string;
  unit?: string;
  source: string;
}

/** Header telemetry pills. */
export const HEADLINE_METRICS: Metric[] = [
  {
    label: "Tier 0 gate p50",
    value: "1.71",
    unit: "ms",
    source: "bench/results/benchmark_results.json → ALWAYS_SHALLOW.latency_ms.p50",
  },
  {
    label: "Adaptive p95",
    value: "2.87",
    unit: "ms",
    source: "bench/results/benchmark_results.json → ADAPTIVE.latency_ms.p95",
  },
  {
    label: "Calibration ECE",
    value: "0.160",
    source:
      "bench/results/benchmark_results.json → ALWAYS_DEEP.hallucination_calibration.ece (n=320)",
  },
  {
    label: "Tests passing",
    value: "150",
    source: "pytest -q — 150 passed",
  },
];

export interface ScrutinyMode {
  mode: string;
  blurb: string;
  p50: number;
  p95: number;
  tier1Rate: number;
  escalationRate: number;
  hallucinationRecall: number | null;
  piiRecall: number | null;
  ece: number | null;
}

/**
 * The three scrutiny configurations the benchmark harness runs, transcribed
 * verbatim from the committed results of the last real run (seed 42, 400
 * labelled interactions).
 */
export const SCRUTINY_MODES: ScrutinyMode[] = [
  {
    mode: "ALWAYS_SHALLOW",
    blurb: "Tier 0 cheap gate only. Fastest, and blind — it catches nothing.",
    p50: 1.711,
    p95: 1.921,
    tier1Rate: 0.0,
    escalationRate: 0.0,
    hallucinationRecall: 0.0,
    piiRecall: 0.0,
    ece: null,
  },
  {
    mode: "ALWAYS_DEEP",
    blurb: "Full Tier 1 pipeline on every response. Total recall, every time paid for.",
    p50: 2.785,
    p95: 2.936,
    tier1Rate: 1.0,
    escalationRate: 0.3075,
    hallucinationRecall: 1.0,
    piiRecall: 1.0,
    ece: 0.16,
  },
  {
    mode: "ADAPTIVE",
    blurb: "Tier 0 decides who earns Tier 1. Near-total recall at ~70% of the deep work.",
    p50: 2.745,
    p95: 2.872,
    tier1Rate: 0.695,
    escalationRate: 0.2625,
    hallucinationRecall: 0.9944444444444445,
    piiRecall: 1.0,
    ece: 0.18381294964028774,
  },
];

export const BENCH_SOURCE = "bench/results/benchmark_results.json — seed 42, 400 interactions";

export interface AppetitePoint {
  appetite: number;
  tier1Rate: number;
  escalationRate: number;
  p50: number;
  p95: number;
  hallucinationRecall: number;
}

/** Risk-appetite sweep: what moving the console slider actually costs and buys. */
export const APPETITE_SWEEP: AppetitePoint[] = [
  { appetite: 0.1, tier1Rate: 0.2, escalationRate: 0.0225, p50: 8.386, p95: 14.69, hallucinationRecall: 0.2222 },
  { appetite: 0.3, tier1Rate: 0.3025, escalationRate: 0.07, p50: 8.948, p95: 15.423, hallucinationRecall: 0.45 },
  { appetite: 0.5, tier1Rate: 0.695, escalationRate: 0.2625, p50: 12.761, p95: 16.342, hallucinationRecall: 0.9944 },
  { appetite: 0.7, tier1Rate: 0.6975, escalationRate: 0.265, p50: 12.778, p95: 15.691, hallucinationRecall: 1.0 },
  { appetite: 0.9, tier1Rate: 0.6975, escalationRate: 0.265, p50: 12.627, p95: 15.833, hallucinationRecall: 1.0 },
];

export const APPETITE_SOURCE =
  "bench/results/appetite_sweep_results.json — seed 42, 400 interactions";

/** The five responsibility pillars the risk vector carries per claim. */
export const PILLARS = [
  { key: "hallucination", label: "Hallucination", color: "#00f0ff" },
  { key: "pii", label: "PII & Secrets", color: "#8b5cf6" },
  { key: "toxicity", label: "Toxicity", color: "#f59e0b" },
  { key: "bias", label: "Demographic Bias", color: "#3b82f6" },
  { key: "policy", label: "Policy Violation", color: "#10b981" },
] as const;

export const DECISIONS = [
  { key: "ALLOW", label: "Allow", color: "#10b981", note: "Untouched. Nothing to remediate." },
  { key: "MODIFY", label: "Modify", color: "#3b82f6", note: "Surgical: hedge, redact, cite, remove." },
  { key: "ESCALATE", label: "Escalate", color: "#f59e0b", note: "A human decides this one." },
  { key: "BLOCK", label: "Block", color: "#ef4444", note: "Reserved. Never for one bad sentence." },
] as const;
