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
silently become a real-world action. See `docs/roadmap.md` for how that
provenance/taint/gating mechanism will be built out (Phase 3).

## Status: Phase 2 (Basic Governance)

This repository is being built incrementally, phase by phase (see
`docs/roadmap.md`). **Phases 1–2 are done; later phases are not
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
- Every request produces a hash-chained audit ledger entry in Postgres,
  plus one entry per claim (verdict, risk labels, provenance,
  remediation).
- Three tenant policies (`configs/*.yaml`) drive different outcomes for
  the same input (e.g. how an UNVERIFIABLE claim is handled differs by
  tenant).

**Known simplifications** (see `docs/roadmap.md` for the full list):
claim verification is a deterministic heuristic, not a real NLI model; PII
detection is regex-based, not Presidio; toxicity/policy/bias labels exist
in the schema but have no detector behind them yet.

**Not yet implemented:** provenance/taint propagation across turns,
tool-call gating, Tier 2 deep verification, the React console, the traffic
replayer, and evaluation/calibration — that's Phase 3 onward.

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
decision, scrutiny tier, and per-claim verdicts/risk labels/remediations.

Select a tenant policy with the `X-ControlPlane-Tenant` header (one of
`customer_support`, `internal_copilot`, `regulated_agent`); it defaults to
`DEFAULT_TENANT` from `.env` otherwise.

## Configuration

Tenant policies live in `configs/*.yaml` and are loaded through
`policy/loader.py` into the `policy.models.Policy` schema — see that file
for what each field currently means (and which fields are schema-only
placeholders for phases not yet built, e.g. `tool_calls`).

## Running tests

```bash
pytest
```

39 tests cover policy loading/validation, the hash-chained audit ledger
(including tamper detection), claim extraction, PII detection, the
heuristic claim verifier, the governance engine's remediation logic
(surgical remediation, multi-label risk, tenant differentiation, hard-block
PII), and the gateway round trip including Scenes 1–3 end to end — see
`tests/unit/` and `tests/integration/`.

## Running the benchmark / demo

Not implemented yet (Phase 4/5). No benchmark numbers exist in this
repository — none will be added until they come from an actual script run,
per the project's no-fabrication rule.
