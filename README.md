# ControlPlane

ControlPlane is an AI governance and safety gateway: it sits between an
application and an AI model/agent, inspects what goes in and comes out, and
lets policy — not silent model behavior — decide whether a response or a
tool call is allowed, modified, escalated, or blocked.

```
Application → ControlPlane Gateway → AI Model → ControlPlane Analysis → Policy Engine → ALLOW / MODIFY / ESCALATE / BLOCK → Application
```

For agents, ControlPlane also intercepts consequential tool calls so an
unverified or tainted claim (e.g. a hallucinated refund amount) can never
silently become a real-world action — this is now implemented end to end,
see Scene 7 below.

## Status: Phase 3 (Agent Safety)

This repository is being built incrementally, phase by phase (see
`docs/roadmap.md`). **Phases 1–3 are done; later phases are not
implemented yet.** Concretely, right now:

- A real client can send an OpenAI-style chat request through the
  ControlPlane gateway, have it forwarded to an upstream OpenAI-compatible
  provider, and get a governed response back.
- Responses go through adaptive scrutiny (Tier 0 cheap gate → Tier 1 full
  pipeline): claim extraction, claim verification against a small fake
  corpus (SUPPORTED/CONTRADICTED/UNVERIFIABLE — UNVERIFIABLE is never
  treated as false), PII detection, and a multi-label risk vector where a
  single claim can be e.g. both `hallucination` and `pii` at once.
- The policy engine applies **surgical remediation** per claim (hedge,
  redact, remove, cite, escalate) rather than blocking a whole response
  for one bad sentence — full-response BLOCK is reserved for deliberate
  cases like a hard-block PII category.
- A claim ControlPlane can't confirm is **tainted**, and that taint
  **propagates across conversation turns**: if a later turn's tool call
  (e.g. `issue_refund(amount=48000)`) uses a value that traces back to an
  unverified/contradicted claim earlier in the same conversation, the
  call is blocked before it ever reaches the application — even if the
  text response itself looked fine.
- A **cost circuit breaker** trips per tenant on request-count or
  token-volume spikes, short-circuiting before the upstream provider is
  ever called (no cost incurred on a tripped request).
- A **cheap-model-first** routing option calls a cheaper model, validates
  its response with the same governance engine, and only retries against
  a stronger model when the checker actually flags a problem.
- Every request produces a hash-chained audit ledger entry in Postgres,
  plus one entry per claim and one per gated tool call.
- Three tenant policies (`configs/*.yaml`) drive different outcomes for
  the same input (e.g. how an UNVERIFIABLE claim is handled, or whether
  tool calls are gated at all, differs by tenant).

**Known simplifications** (see `docs/roadmap.md` for the full list):
claim verification is a deterministic heuristic, not a real NLI model; PII
detection is regex-based, not Presidio; taint matching is numeric-value
only; the cost breaker is in-memory/per-process, not Redis-backed;
toxicity/policy/bias risk labels exist in the schema but have no detector
behind them yet.

**Not yet implemented:** Tier 2 deep verification, the React console, the
traffic replayer, and evaluation/calibration — that's Phase 4/5.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env   # fill in UPSTREAM_API_KEY, etc.
docker compose up -d postgres

uvicorn gateway.main:app --reload
```

Then point any OpenAI client at `http://localhost:8000/v1` instead of the
real provider's base URL — the request is forwarded, governed, and
audited. The response carries a `controlplane` extension field with the
decision, scrutiny tier, per-claim verdicts/risk labels/remediations, and
any tool-call gating decisions.

Select a tenant policy with the `X-ControlPlane-Tenant` header (one of
`customer_support`, `internal_copilot`, `regulated_agent`); it defaults to
`DEFAULT_TENANT` from `.env` otherwise. Multi-turn taint tracking needs a
stable `conversation_id`, passed via the request body's `controlplane`
extension object: `{"controlplane": {"conversation_id": "..."}}`.

## Configuration

Tenant policies live in `configs/*.yaml` and are loaded through
`policy/loader.py` into the `policy.models.Policy` schema. The shared tool
sink catalog (which tool names map to which consequence category, e.g.
`issue_refund` → `money_movement`) lives in `data/tools.yaml`, loaded via
`policy/tools.py` — see those files for what each field means.

## Running tests

```bash
pytest
```

61 tests cover policy loading/validation, the hash-chained audit ledger
(including tamper detection), claim extraction, PII detection, the
heuristic claim verifier, the governance engine's remediation logic,
taint lookup across conversation turns, tool-call gating, the cost
breaker, and the gateway round trip including Scenes 1–3 and 5–7 end to
end — see `tests/unit/` and `tests/integration/`.

## Running the benchmark / demo

Not implemented yet (Phase 4/5). No benchmark numbers exist in this
repository — none will be added until they come from an actual script run,
per the project's no-fabrication rule.
