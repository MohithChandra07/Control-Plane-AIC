# ControlPlane

<div align="center">

![status](https://img.shields.io/badge/Status-Phase%205%20%E2%80%94%20Done-22C55E?style=for-the-badge)
![tests](https://img.shields.io/badge/Tests-169%20Passing-22C55E?style=for-the-badge)
![python](https://img.shields.io/badge/Language-Python%203.11%2B-00599C?style=for-the-badge&logo=python&logoColor=white)
![web](https://img.shields.io/badge/Web_Console-Next.js%20%2F%20React-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)
![license](https://img.shields.io/badge/License-MIT-lightgrey?style=for-the-badge)
![Track](https://img.shields.io/badge/Accenture_AIC-Prototype_Development-DC2626?style=for-the-badge)
![Institute](https://img.shields.io/badge/IIT%20Patna-TLE_Error-1D4ED8?style=for-the-badge)

<br/>

**An AI governance and safety gateway. ControlPlane sits between an application and an AI model/agent, inspects what goes in and comes out, and lets policy — not silent model behavior — decide whether a response or a tool call is allowed, modified, escalated, or blocked.**

<br/>

*Mohith Chandra Gugulothu · Monal Gupta · Veda Vikas · IIT Patna*

</div>

---

## What is this project?

LLM outputs can hallucinate facts, leak PII, or hand an agent a number to act on that was never actually verified. Most teams find out after the bad response already reached a user, or after the agent already called a tool.

**ControlPlane** sits in that gap: every response is checked *before* it ships, every consequential tool call is checked *before* it fires, and every decision is written to a tamper-evident audit trail — so the answer to "why did the model do that" is always a lookup, never a guess.

![ControlPlane 3D WebGL Showcase](docs/assets/hero_3d_showcase.png)

```
Application → ControlPlane Gateway → AI Model → ControlPlane Analysis
            → Policy Engine → ALLOW / MODIFY / ESCALATE / BLOCK → Application
```

For agents, ControlPlane also intercepts consequential tool calls so an unverified or tainted claim (e.g. a hallucinated refund amount) can never silently become a real-world action. Implemented end to end — see Scene 7 in [`docs/roadmap.md`](docs/roadmap.md).

## Contents

- [Status](#status)
- [What's implemented](#whats-implemented)
- [Adaptive Scrutiny Architecture](#adaptive-scrutiny-architecture)
- [Quick start](#quick-start)
- [Example: a governed request](#example-a-governed-request)
- [Project layout](#project-layout)
- [Configuration](#configuration)
- [Tests](#tests)
- [Benchmark](#benchmark)
- [Console](#console)
- [Troubleshooting](#troubleshooting)
- [Documentation](#documentation)
- [Team \& Contributors](#team--contributors)

---

## Status

**Phase 5 (Calibration + Demo Hardening) — all 5 phases done.** Built incrementally; see [`docs/roadmap.md`](docs/roadmap.md) for the full history.

---

## What's implemented

| Area | Behavior |
|---|---|
| **Gateway** | Real OpenAI-compatible chat requests are forwarded to an upstream provider and returned governed. |
| **Scrutiny** | Adaptive two-tier pipeline (Tier 0 cheap gate → Tier 1 full pipeline): claim extraction, claim verification against a fake corpus (`SUPPORTED` / `CONTRADICTED` / `UNVERIFIABLE` — unverifiable is never treated as false), PII detection, and a multi-label risk vector (a claim can be both `hallucination` *and* `pii` at once). |
| **Remediation** | Surgical, per-claim (hedge, redact, remove, cite, escalate) — full-response `BLOCK` is reserved for deliberate cases like a hard-block PII category. |
| **Taint tracking** | An unconfirmed claim is *tainted*, and taint propagates across conversation turns: if a later tool call (e.g. `issue_refund(amount=48000)`) traces back to an unverified/contradicted claim, it's blocked before it reaches the application. |
| **Cost control** | A per-tenant circuit breaker trips on request-count or token-volume spikes, short-circuiting before the upstream provider is called. An optional cheap-model-first router validates a cheap model's response with the same governance engine and only escalates to a stronger model on failure. |
| **Audit** | Every request produces a hash-chained ledger entry, plus one entry per claim and one per gated tool call. |
| **Multi-tenant policy** | Three tenant policies (`configs/*.yaml`) drive different outcomes for identical input. |
| **Benchmarking** | A harness (`bench/`) runs a 400-item labeled synthetic dataset through the real gateway under three scrutiny configurations, reporting measured precision/recall/latency — see [`docs/roadmap.md`](docs/roadmap.md) for the latest numbers. |
| **Console** | A traffic replayer (`demo/replayer/`, measured: 10,000 interactions in ~100s) plus a read/write API (`console/backend/`) and React dashboard (`console/frontend/` & `showcase/`) showing decision breakdown, latency, a recent-requests table, per-request claim/tool-call drill-down, a live risk-appetite slider, and human review (Agree/Disagree). |
| **Calibration** | Expected Calibration Error (`bench/metrics/calibration.py`) computed from real (score, outcome) pairs; a live risk-appetite control (`policy/appetite.py`) needs no restart or YAML edit — both measured in [`docs/evaluation.md`](docs/evaluation.md). |
| **Human review loop** | Reviewers mark decisions Agree/Disagree in the console; once disagreement on `ESCALATE`/`BLOCK` crosses a threshold, `policy/recalibration.py` *suggests* (never auto-applies) a risk-appetite change. |
| **Injection defense** | `detectors/injection.py` scans untrusted (`role="tool"`/`"function"`) messages for instruction-override phrasing and neutralizes matches before the request reaches the upstream model. A user's own `role="user"` message is never scanned this way. |

---

## Development Workflow & Roadmap

The project was executed incrementally across five milestones, ensuring comprehensive testing and architectural validation at every stage:

* **Phase 1: Foundations & Architecture**
  * Built the OpenAI-compatible proxy gateway (`/v1/chat/completions`) and multi-tenant policy loader (`policy/loader.py`).
  * Designed the PostgreSQL-backed cryptographically hash-chained audit ledger to record all transactional state changes.
* **Phase 2: Claim Scrutiny & Safety Pipelines**
  * Integrated the Tier 0/Tier 1 adaptive scrutiny pipeline to dynamically route payload claims.
  * Implemented NLP sentence claim extraction, fact-checking against a custom knowledge corpus, and regex PII scanners.
* **Phase 3: Cost Control & Safety Nets**
  * Built per-tenant rate/token volume circuit breakers and cheap-model-first routing with automated escalation on failure.
  * Added prompt-injection scanners for untrusted tool outputs to neutralize hijack attempts.
* **Phase 4: Action Gating & Taint Propagation**
  * Engineered cross-turn taint tracking to lock unverified claims to downstream tool execution parameters.
  * Added the action sink catalog (`data/tools.yaml`) to block consequential tool calls (e.g. monetary transactions) automatically.
* **Phase 5: UI Management Console & Dynamic Calibration**
  * Developed the Next.js WebGL 3D showcase landing page and live interactive console dashboard.
  * Integrated expected calibration error (ECE) computations and automated recalibration engines driven by live human reviewer agreements.

---

## Adaptive Scrutiny Architecture

![Adaptive Scrutiny Configurations](docs/assets/adaptive_scrutiny.png)

Depth is earned, not spent uniformly. A lightweight Tier 0 pre-filter evaluates every payload first. Only when confidence falls below the tenant's scrutiny threshold does the full Tier 1 claim extraction, corpus verification, and PII inspection pipeline engage.

**Known simplifications** — full list in [`docs/assumptions.md`](docs/assumptions.md):
claim verification is a deterministic heuristic, not a real NLI model · PII detection is regex-based, not Presidio · taint matching is numeric-value only · the cost breaker is in-memory/per-process, not Redis-backed · toxicity/policy/bias risk labels exist in the schema with no detector behind them yet · no metric is computed for `policy_violation` (labeled but undetected) · human agreement is real but not backfilled · recalibration is suggestion-only · Tier 2 deep verification isn't implemented.

---

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env   # fill in UPSTREAM_API_KEY, etc.
docker compose up -d postgres

uvicorn gateway.main:app --reload
```

Point any OpenAI client at `http://localhost:8000/v1` instead of the real provider's base URL. The request is forwarded, governed, and audited; the response carries a `controlplane` extension field with the decision, scrutiny tier, per-claim verdicts/risk labels/remediations, and any tool-call gating decisions.

- **Tenant selection:** `X-ControlPlane-Tenant` header — one of `customer_support`, `internal_copilot`, `regulated_agent` — defaults to `DEFAULT_TENANT` from `.env`.
- **Multi-turn taint tracking** needs a stable `conversation_id` in the request body: `{"controlplane": {"conversation_id": "..."}}`.

---

## Example: a governed request

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-ControlPlane-Tenant: customer_support" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "What is our refund policy?"}],
    "controlplane": {"conversation_id": "conv-123"}
  }'
```

The response is a normal OpenAI chat completion with one extra field — `controlplane` — carrying the full governance trace:

```jsonc
{
  "id": "chatcmpl-...",
  "choices": [{ "message": { "role": "assistant", "content": "..." } }],
  // ...standard OpenAI fields...
  "controlplane": {
    "request_id": "req-...",
    "tenant_id": "customer_support",
    "decision": "MODIFY",
    "latency_ms": 842.15,
    "tier": 1,
    "turn_id": 1,
    "model_used": "gpt-4o-mini",
    "rerouted": false,
    "injection_detections": [],
    "claims": [
      {
        "claim_id": "claim-1",
        "text": "Refunds are processed within 30 days.",
        "verdict": "SUPPORTED",
        "risk_labels": [],
        "risk": { "hallucination": 0.0, "pii": 0.0 },
        "remediation": null,
        "taint_status": "clean"
      }
    ],
    "tool_calls": []
  }
}
```

`decision`, `tier`, and every field under `claims`/`tool_calls` are exactly what drives the console's drill-down view — nothing shown there is derived separately from what the gateway itself returns.

---

## Project layout

```
gateway/      OpenAI-compatible HTTP entrypoint, provider adapters, cost
              breaker, cheap-model reroute, tool-call gating (spec §9, §11, §17)
policy/       Policy schema/loader, governance engine, risk appetite,
              recalibration suggestions, tool sink catalog
detectors/    Claim extraction, heuristic claim verification, PII (regex),
              prompt-injection scanning, Tier 0 cheap gate
ledger/       Hash-chained audit ledger, cross-turn taint lookup, DB models
configs/      Per-tenant policy YAML (customer_support, internal_copilot,
              regulated_agent)
data/         Shared tool sink catalog + fake verification corpus
bench/        400-item labeled synthetic dataset, harness, ECE/calibration
              metrics, results
demo/         Traffic replayer for populating the console with real ledger data
console/      Read/write API (backend/) + React dashboard (frontend/)
showcase/     Next.js 14 WebGL 3D showcase site & integrated console
docs/         Architecture, terminology, policy breakdown, demo scenarios,
              evaluation numbers, known simplifications
tests/        169 unit + integration tests, incl. all 9 demo scenes
              end-to-end
```

---

## Configuration

Tenant policies live in `configs/*.yaml`, loaded via `policy/loader.py` into the `policy.models.Policy` schema. The shared tool sink catalog (which tool names map to which consequence category, e.g. `issue_refund` → `money_movement`) lives in `data/tools.yaml`, loaded via `policy/tools.py`. See those files for field-level docs.

---

## Tests

```bash
pytest
```

![Test Suite & Benchmark Execution](docs/assets/test_benchmark_terminal.png)

169 tests across `tests/unit/` and `tests/integration/` cover policy loading/validation, the hash-chained audit ledger (incl. tamper detection), claim extraction/verification, PII detection, remediation logic, cross-turn taint lookup, tool-call gating, the cost breaker, prompt-injection detection, risk-appetite scaling, recalibration suggestions, calibration/ECE metrics, the benchmark dataset generator and harness, the traffic replayer, the console backend (incl. human review), and the gateway round trip through all 9 demo scenes end to end. See [`docs/demo-scenarios.md`](docs/demo-scenarios.md) for which test proves which scene.

---

## Benchmark

```bash
python -m bench.harness.run_benchmark
```

Runs the 400-item labeled synthetic dataset (`bench/dataset/generate.py`) through the real gateway under three scrutiny configurations (`ALWAYS_SHALLOW` / `ALWAYS_DEEP` / `ADAPTIVE`), writing results to `bench/results/benchmark_results.json`. See [`docs/roadmap.md`](docs/roadmap.md) for the latest numbers and why cost isn't reported as a dollar figure in this harness.

---

## Console

![Governance Console Overview](docs/assets/governance_console.png)

**1. Populate it with traffic:**

```bash
python -m demo.replayer.replay --count 10000
```

Posts synthetic interactions through the real gateway to a local SQLite file (`demo/replayer/traffic.db` by default — pass `--database-url` to target real Postgres instead).

**2. Run it:**

```bash
# Terminal 1 — read-only API over the audit ledger
DATABASE_URL="sqlite+aiosqlite:///$(pwd)/demo/replayer/traffic.db" \
  uvicorn console.backend.main:app --port 8002

# Terminal 2 — 3D Showcase & Console (Next.js)
cd showcase && npm install && npm run dev
```

Open `http://localhost:3000/console` (or `http://localhost:5173/` for the Vite dashboard). It auto-refreshes every 5 seconds and reads only from the audit ledger — nothing shown is hard-coded demo data.

Select a tenant to see (and set) its live risk-appetite slider and human review panel. Click a request row for a claim/tool-call drill-down, then click Agree/Disagree — `GET /api/human-agreement/{tenant}` and, once enough disagreement accumulates, `GET /api/recalibration/{tenant}`'s suggestion banner update immediately, no reload. See [`docs/demo-scenarios.md`](docs/demo-scenarios.md), Scene 9.

---

## Troubleshooting

**Gateway won't start / can't reach Postgres.**
Confirm `docker compose up -d postgres` is actually running (`docker compose ps`) and that `DATABASE_URL` in `.env` matches the `postgres:16-alpine` service in `docker-compose.yml` (`postgresql+asyncpg://controlplane:controlplane@localhost:5432/controlplane` by default). The container's healthcheck must pass before the gateway can connect.

**401/403 from the upstream provider.**
`UPSTREAM_API_KEY` in `.env` is still the placeholder (`sk-replace-me`) or invalid. `UPSTREAM_BASE_URL` and `UPSTREAM_DEFAULT_MODEL` must also point at a real OpenAI-compatible endpoint/model.

**Taint tracking isn't catching a later tool call.**
Multi-turn taint lookup keys on `conversation_id`. If it's omitted, or changes between turns, ControlPlane has no way to link the tool call back to the earlier unverified claim — pass the same `{"controlplane": {"conversation_id": "..."}}` on every turn.

**Console dashboard shows no data.**
The dashboard only reads from the audit ledger — it won't show anything until you've run the replayer (or sent real traffic through the gateway) *against the same database* the console backend's `DATABASE_URL` points to.

**`pytest` fails after a fresh clone.**
Make sure you installed with the `dev` extra: `pip install -e ".[dev]"` — a plain `pip install -e .` skips `pytest`, `pytest-asyncio`, `aiosqlite`, and `ruff`.

**Benchmark run looks stale.**
`bench/results/benchmark_results.json` is only overwritten when you run `python -m bench.harness.run_benchmark` yourself — the numbers in `docs/roadmap.md` are a snapshot from the last run in this repo, not a live value.

---

## Documentation

| Doc | Covers |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | System diagrams and component boundaries |
| [`docs/terminology.md`](docs/terminology.md) | Shared vocabulary (tier, taint, sink, remediation, etc.) |
| [`docs/policies.md`](docs/policies.md) | Per-tenant policy breakdown |
| [`docs/roadmap.md`](docs/roadmap.md) | Phase history, demo scenes, latest benchmark numbers |
| [`docs/evaluation.md`](docs/evaluation.md) | Measured calibration and risk-appetite effects |
| [`docs/demo-scenarios.md`](docs/demo-scenarios.md) | All 9 demo scenes with exact reproduce commands and the test proving each |
| [`docs/assumptions.md`](docs/assumptions.md) | Full list of known simplifications |
| [`docs/project-brief.md`](docs/project-brief.md) | Original project brief |

---

## Team & Contributors

This prototype was developed for the Accenture Innovation Challenge 2026 by:

* **[Mohith Chandra](https://github.com/MohithChandra07)** — Team Lead & Core Engineer
* **[Monal Gupta](https://github.com/monalgupta89-coder)** — Core NLP & Fullstack Developer
* **[Veda Vikas](https://github.com/VEDAVIKASD)** — System Architect & Developer

---

<div align="center">

**We have done work.**  
*Mohith Chandra Gugulothu 
· Monal Gupta 
· Veda Vikas*  
**IIT Patna**

</div>
