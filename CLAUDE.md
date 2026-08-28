# CLAUDE.md

Guidance for whoever (human or agent) works on ControlPlane next.

## What this is

ControlPlane is an AI governance/safety gateway. Full spec context lives in
the task history that created this repo; the living summary is
`README.md` (current state) and `docs/roadmap.md` (phase-by-phase plan and
status — keep it truthful, update it only when a phase's definition of done
is actually met).

## Operating rules that apply to every change here

1. **Build vertically, phase by phase** (`docs/roadmap.md`). Don't start a
   later phase's detectors before the current phase's end-to-end slice
   works and is tested.
2. **Never fabricate numbers.** No benchmark/latency/eval number goes into
   README, docs, or code comments unless it came from an actual script run
   in this session.
3. **UNVERIFIABLE is not FALSE.** Don't collapse the three verification
   verdicts (SUPPORTED/CONTRADICTED/UNVERIFIABLE) into two.
4. **Policy lives in `configs/*.yaml`**, loaded via `policy/loader.py`
   into `policy.models.Policy`. Don't hardcode tenant-specific thresholds
   or behavior in Python.
5. **Audit everything that matters.** Any new decision path should go
   through `ledger.audit.AuditLedger.record()` so the hash chain stays a
   complete history — don't add a second, unaudited way to make a
   governance decision.
6. **Fail-open vs fail-closed is explicit, per tenant, never silent.**
   When adding a detector/service call, decide what happens on its failure
   and make sure it's observable (audit `error` field), not swallowed.
7. Run `pytest` and `ruff check .` before considering a change done.

## Repo layout (as of Phase 5 — all phases done)

```
gateway/    FastAPI app, OpenAI-compatible routes, provider abstraction,
            middleware/ (cost circuit breaker); routes/chat.py resolves
            live risk appetite (_effective_policy) and neutralizes
            prompt-injection attempts in untrusted messages before any
            provider call
policy/     Policy schema (Pydantic) + YAML loader + governance engine
            (engine.py) + tool sink catalog loader (tools.py) + tool-call
            gating (tool_gate.py) + risk appetite scaling (appetite.py) +
            recalibration suggestion logic (recalibration.py)
detectors/  Claim extraction, Tier 0 gate, PII detector, heuristic claim
            verifier, prompt-injection detector (injection.py — scans only
            role="tool"/"function" messages)
data/       corpus/ — fake enterprise docs the claim verifier grounds against;
            tools.yaml — shared tool sink catalog (not per-tenant, so it's
            not under configs/ where the policy loader globs *.yaml)
ledger/     SQLAlchemy audit models (incl. TenantSetting for risk appetite),
            hash-chained writer, Postgres schema, taint.py — taint lookup
            queried against the audit ledger itself (no second, unaudited
            datastore); AuditEvent.kind discriminates request/claim/
            tool_call/risk_appetite_change/human_review rows
configs/    One YAML policy per tenant
bench/      dataset/ (synthetic labeled data generator), metrics/ (P/R,
            latency percentiles, cost calc, calibration.py — ECE/reliability
            bins), harness/ (one-command ALWAYS_SHALLOW/ALWAYS_DEEP/ADAPTIVE
            benchmark + run_appetite_sweep.py), results/ (committed output
            from the last real run), pricing.yaml (illustrative,
            labeled-as-assumed $/1K-token rates)
demo/       replayer/ — one-command synthetic traffic generator that
            populates the audit ledger for the console
console/    backend/ — small FastAPI service over audit_events, read plus
            two narrowly-scoped admin writes (risk appetite, human review);
            frontend/ — Vite+React dashboard, incl. RiskAppetiteControl and
            HumanFeedbackPanel components
docs/       project-brief.md, terminology.md, policies.md, assumptions.md,
            architecture.md (Mermaid diagrams), demo-scenarios.md (all 9
            scenes, reproducible by exact test name), evaluation.md (every
            number transcribed from an actual script run), roadmap.md
tests/      unit/ (no I/O) and integration/ (async DB + TestClient)
```

All phases (1–5) from `docs/roadmap.md` are done; see that file's Phase 5
section and `docs/assumptions.md` for what's a documented simplification
versus what's fully implemented (e.g. Tier 2 deep verification is still
not built).

## Running things

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
pytest
ruff check .
docker compose up -d postgres   # for running the gateway against real Postgres
uvicorn gateway.main:app --reload
```

Tests use an isolated file-backed SQLite DB and a fake provider — they
don't require Postgres or a real upstream API key.
