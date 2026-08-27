# Policies

Policy lives in `configs/*.yaml`, loaded through `policy/loader.py` into
the `policy.models.Policy` schema. Nothing tenant-specific is hardcoded
in Python (`CLAUDE.md` rule #4) — adding a fourth tenant means adding a
fourth YAML file, not touching `gateway/` or `policy/engine.py`.

## Schema fields (`policy/models.py`)

| Field | Controls |
|---|---|
| `latency_budget_ms` | Informational target; not yet enforced as a hard cutoff (see `docs/assumptions.md`). |
| `allowed_remediations` | Which of ALLOW/HEDGE/REDACT/REMOVE/ADD_CITATION/ESCALATE/BLOCK this tenant permits. If the engine picks a remediation not on this list, it falls back to ESCALATE. |
| `unverifiable_handling` | What happens to an `UNVERIFIABLE` claim: ALLOW, HEDGE, ESCALATE, or BLOCK. |
| `risk_thresholds` | `tier1_trigger` (Tier 0 → Tier 1 gate), `tier2_trigger` (CONTRADICTED → ESCALATE vs REMOVE), `block_trigger` (present in the schema; see `docs/assumptions.md` for where it's and isn't wired up). Must satisfy `tier1 <= tier2 <= block`. |
| `pii` | `enabled`, default `remediation` for detected PII, `hard_block_categories` (any of these present forces a whole-response BLOCK). |
| `tool_calls` | `enabled`, `consequential_sinks` this tenant cares about, `tainted_argument_action`, `require_verified_provenance` (schema-present, not yet separately enforced — see `docs/assumptions.md`). |
| `escalation` | `enabled`, `max_escalation_rate` (schema-present target, not yet enforced as a hard cap). |
| `cost_breaker` | `enabled`, `window_seconds`, `max_requests_per_window`, `max_tokens_per_window`. |
| `model_routing` | `enabled`, `cheap_model`, `escalation_model`. |
| `fail_mode` | `fail_open` or `fail_closed` — governs whether an ESCALATEd claim/tool-call is stripped from the response (closed) or delivered with a flag (open) when the tenant's policy doesn't otherwise resolve it. |

The shared **tool sink catalog** (`data/tools.yaml`, loaded via
`policy/tools.py`) is deliberately *not* under `configs/` — `policy/loader.py`
globs `configs/*.yaml` as tenant policies, and a tool's nature (what sink
category `issue_refund` belongs to) doesn't vary per tenant the way a
threshold does.

## The three tenants

### `customer_support` — Customer Support Assistant

Customer-facing, high external risk, conservative. 150ms latency budget.
`unverifiable_handling: HEDGE` — don't state what you can't confirm, but
don't refuse to answer either. PII redacted by default; credit
card/government ID hard-blocked. Tool calls disabled (no consequential
actions in this tenant's scope). `fail_mode: fail_closed`.

### `internal_copilot` — Internal Knowledge Copilot

Internal-only, more tolerant. 600ms latency budget, loosest
`risk_thresholds` of the three. `unverifiable_handling: ALLOW` — the
audience can cross-check against internal systems themselves, so an
unconfirmed claim isn't hedged or blocked, just passed through (still
audited, still labeled `UNVERIFIABLE` internally). `fail_mode: fail_open`.

### `regulated_agent` — Regulated Decision-Support Agent

Consequential tool access (e.g. `issue_refund`), strictest verification.
2s latency budget (room for real scrutiny). Tightest `risk_thresholds` of
the three. `unverifiable_handling: ESCALATE` — never silently allow or
even just hedge an unconfirmed claim, put a human in the loop. Tool calls
enabled with `money_movement`/`database_write`/`external_communication`
as consequential sinks, `tainted_argument_action: BLOCK` — this is the
tenant Scene 7 (tainted refund) runs against. `model_routing.enabled:
false` — this tenant isn't a cost-optimization target, always use the
primary model. `fail_mode: fail_closed`.

## Same input, different outcomes

`tests/integration/test_scene8_tenant_differentiation.py` sends the exact
same unverifiable claim through all three tenants and gets three
genuinely different, policy-driven outcomes:

| Tenant | Remediation | Response decision |
|---|---|---|
| `customer_support` | HEDGE | MODIFY |
| `internal_copilot` | ALLOW | ALLOW |
| `regulated_agent` | ESCALATE | ESCALATE |

Same detector output (same verdict, same risk score) — three different
actions, because policy differs, not detection.

## Risk appetite: adjusting a tenant's posture live

`policy/appetite.py`'s `apply_risk_appetite()` scales a tenant's own
`risk_thresholds` around their configured baseline (0.5 = no change),
set live via the console (`PUT /api/risk-appetite/{tenant}`,
`gateway/routes/chat.py` reads it fresh on every request — no restart
needed) rather than by editing YAML. It scales *relative to* each
tenant's own configuration, so `regulated_agent` stays relatively
stricter than `customer_support` at the same appetite setting — appetite
adjusts caution, it doesn't erase the policy differentiation between
tenants. See `docs/evaluation.md` for the measured effect.
