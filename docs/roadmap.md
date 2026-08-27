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
