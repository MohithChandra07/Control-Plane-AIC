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
provenance/taint/gating mechanism will be built out.

## Status: Phase 1 (Foundation)

This repository is being built incrementally, phase by phase (see
`docs/roadmap.md`). **Phase 1 is done; later phases are not implemented
yet.** Concretely, right now:

- A real client can send an OpenAI-style chat request through the
  ControlPlane gateway, have it forwarded to an upstream OpenAI-compatible
  provider, and get the response back.
- Every request produces a hash-chained audit ledger entry in Postgres
  (tenant, decision, latency, error if any).
- Three tenant policies (`configs/*.yaml`) are defined and independently
  resolved per request, validated against a shared Pydantic schema.

**Not yet implemented:** claim extraction/verification, risk labeling,
surgical remediation, provenance/taint tracking, tool-call gating, adaptive
scrutiny tiers, the React console, the traffic replayer, and evaluation/
calibration. The gateway currently always decides `ALLOW` (or `ERROR` if the
upstream call fails) — there is no detection or policy enforcement logic
yet. Don't read anything into the `decision` field beyond "the upstream call
succeeded or didn't."

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env   # fill in UPSTREAM_API_KEY, etc.
docker compose up -d postgres

uvicorn gateway.main:app --reload
```

Then point any OpenAI client at `http://localhost:8000/v1` instead of the
real provider's base URL — the request is forwarded and audited.

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

12 tests currently cover policy loading/validation, the hash-chained audit
ledger (including tamper detection), and the gateway round trip (clean
request, unknown tenant, upstream failure, and per-tenant policy
resolution) — see `tests/unit/` and `tests/integration/`.

## Running the benchmark / demo

Not implemented yet (Phase 4/5). No benchmark numbers exist in this
repository — none will be added until they come from an actual script run,
per the project's no-fabrication rule.
