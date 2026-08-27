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

## Phase 4 — Observability + Evaluation (not started)

React console, traffic replayer (~10k interactions), benchmark harness,
latency/cost measurement, evaluation charts.

## Phase 5 — Calibration + Demo Hardening (not started)

ECE/calibration, risk-appetite control wired to real policy behavior,
human override + recalibration loop, final demo scenarios, full docs.
