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

## Phase 2 — Basic Governance (not started)

Tier 0/Tier 1 scrutiny, claim extraction, claim verification
(SUPPORTED/CONTRADICTED/UNVERIFIABLE), PII detection, multi-label risk
vector, policy engine enforcement, surgical remediation. Target: Scenes
1–3 work end-to-end.

## Phase 3 — Agent Safety (not started)

Provenance, taint propagation across turns, tool-call interception, sink
classification, action gating, retry/cost circuit breakers. Target: Scenes
5–7 (Scene 7 — tainted refund blocked — is the critical one).

## Phase 4 — Observability + Evaluation (not started)

React console, traffic replayer (~10k interactions), benchmark harness,
latency/cost measurement, evaluation charts.

## Phase 5 — Calibration + Demo Hardening (not started)

ECE/calibration, risk-appetite control wired to real policy behavior,
human override + recalibration loop, final demo scenarios, full docs.
