# Architecture

## System overview

```mermaid
flowchart LR
    App[Application] -->|OpenAI-compatible request| GW[ControlPlane Gateway]
    GW -->|scripted/real provider call| LLM[AI Model]
    LLM -->|response| GW
    GW -->|governed response| App

    GW -.writes.-> Ledger[(Audit Ledger\nPostgres/SQLite)]
    GW -.reads risk appetite.-> Ledger
    Console[Console Backend] -.reads.-> Ledger
    Console -.writes appetite/reviews.-> Ledger
    Frontend[Console Frontend] -->|fetch| Console
```

The gateway (`gateway/`) and the console (`console/backend/`) are
deliberately separate processes sharing one database — an introspection
surface has no business running in the same process as the thing being
introspected, and the console needs write access for two narrowly-scoped
admin actions (risk appetite, human review) that the gateway itself never
needs.

## Request flow

```mermaid
flowchart TD
    A[POST /v1/chat/completions] --> B{Cost breaker\ncheck_and_record}
    B -->|tripped| C[429, audited, no provider call]
    B -->|ok| D[Resolve tenant policy\n+ live risk appetite]
    D --> E[Neutralize injection attempts\nin tool/function messages]
    E --> F{model_routing\nenabled?}
    F -->|yes| G[Call cheap_model]
    F -->|no| H[Call requested model]
    G --> I[Governance engine\nevaluates response]
    I -->|ESCALATE/BLOCK| J[Retry against\nescalation_model]
    I -->|ALLOW/MODIFY| K[Response governance flow]
    J --> K
    H --> K
    K --> L[Tool-call gating]
    L --> M[Audit: request + claim rows\n+ tool_call rows]
    M --> N[Return governed response]
```

Cost breaker → tenant/appetite resolution → input-side injection
neutralization → model call (with optional cheap-model reroute) →
response governance → tool-call gating → audit → response, in that order.
Each stage can short-circuit the rest (a tripped breaker never calls the
provider; a `ProviderError` skips straight to the audited-error response).

## Response (claim) flow

```mermaid
flowchart TD
    A[Response text] --> B{Tier 0\nquick_risk_score}
    B -->|below tier1_trigger| C[ALLOW, unchanged,\nno claims extracted]
    B -->|at/above tier1_trigger| D[extract_claims\nspan-tracked sentences]
    D --> E[Per claim: PII detect\n+ claim verify]
    E --> F[Risk vector\nhallucination + pii]
    F --> G[Per-claim remediation\npolicy-driven]
    G --> H{Any claim BLOCK?}
    H -->|yes| I[Whole response replaced\nwith fixed BLOCK_MESSAGE]
    H -->|no| J[Reconstruct text:\nredact/hedge/remove/cite\nper claim, in place]
    J --> K[Aggregate decision =\nmost severe per-claim outcome]
```

This is Phase 2's core mechanism (`policy/engine.py:GovernanceEngine`).
The "surgical" property comes from step J: claims are processed by their
original character spans, so only the flagged sentence changes — the rest
of the response is copied through untouched.

## Provenance flow

```mermaid
flowchart LR
    Claim[Claim text] --> Verify[ClaimVerifier.verify]
    Corpus[(data/corpus/*.md)] --> Verify
    Verify --> Verdict[SUPPORTED /\nCONTRADICTED /\nUNVERIFIABLE]
    Verify --> Prov[Provenance:\nsource, source_id,\nverdict, turn_id]
    Prov --> Audit[(audit_events row,\nkind=claim)]
```

Every claim's provenance names *where its verdict came from* — a specific
corpus document (`source=retrieved_doc`, `source_id=<doc>`) or nothing
found (`source=model_prior`). `turn_id` is the count of user-role
messages in the request (`gateway/routes/chat.py:_turn_id`) — computed
statelessly per request, since an OpenAI-style client resends full
conversation history on every call, so there's no session store to keep
in sync.

## Taint flow (Scene 7)

```mermaid
sequenceDiagram
    participant App
    participant GW as Gateway
    participant Ledger as Audit Ledger
    App->>GW: Turn 1: "what's the customer owed?"
    GW->>GW: Claim "owed ₹48,000" -> UNVERIFIABLE
    GW->>Ledger: audit claim row (verdict=UNVERIFIABLE,\ntaint_status=tainted, claim_text)
    App->>GW: Turn 2: agent calls issue_refund(amount=48000)
    GW->>Ledger: find_taint(conversation_id, 48000)
    Ledger-->>GW: match: turn 1's tainted claim
    GW->>GW: tainted_argument_action = BLOCK
    GW-->>App: tool_calls stripped from response,\ndecision=BLOCK
    GW->>Ledger: audit tool_call row\n(remediation=BLOCK, tainted_args)
```

A claim is tainted the moment its verdict isn't `SUPPORTED`
(`policy/engine.py`). Taint propagation isn't a separate datastore — `ledger/taint.py`
queries the same hash-chained `audit_events` table the gateway already
writes to (`claim_text` was added to the schema specifically so there's
something to match a later argument against), matching on the underlying
number regardless of currency/comma formatting. No second, unaudited way
to track what's trustworthy (`CLAUDE.md` rule #5).

## Tool-call flow (Scene 7, general case)

```mermaid
flowchart TD
    A[Response has tool_calls] --> B{policy.tool_calls\n.enabled?}
    B -->|no| C[ALLOW, ungated]
    B -->|yes| D{Tool's sink in\nconsequential_sinks?}
    D -->|no| C
    D -->|yes| E[For each tainted_arg:\nledger.taint.find_taint]
    E --> F{Any match?}
    F -->|no| G[ALLOW]
    F -->|yes| H[tainted_argument_action\nBLOCK / ESCALATE / ALLOW]
    H --> I{BLOCK, or ESCALATE\nunder fail_closed?}
    I -->|yes| J[Call stripped from\nmessage.tool_calls]
    I -->|no| K[Call kept, flagged\nin audit + response]
```

Sink classification (`data/tools.yaml` + `policy/tools.py`) is shared
across tenants — a tool's nature doesn't change per tenant. What differs
per tenant is whether a sink is *consequential for them* and what happens
on a tainted argument, both in `policy.tool_calls`.

## Audit ledger shape

One append-only, hash-chained table (`ledger/models.py:AuditEvent`),
discriminated by an explicit `kind` column rather than inferring row type
from which fields happen to be populated (added in Phase 4 after a real
collision: request rows carrying model-routing info and tool_call rows
both populate `action`, so that field alone couldn't tell them apart):

| `kind` | One row per | Key fields |
|---|---|---|
| `request` | gateway call | `decision`, `latency_ms`, `action` (model routing / injection info) |
| `claim` | extracted claim | `claim_id`, `claim_text`, `verdict`, `risk_labels`, `provenance`, `taint_status`, `remediation` |
| `tool_call` | gated `tool_calls` entry | `remediation`, `action` (tool_name/sink/tainted_args) |
| `risk_appetite_change` | console appetite write | `action` (old/new appetite, updated_by) |
| `human_review` | console review submission | `action` (reviewed_request_id/claim_id/decision, reviewer, agree, notes) |

`ledger/audit.py`'s `hash` commits to the previous row's hash plus the
row's own canonical field values — `verify_chain()` recomputes the whole
chain and catches any retroactive edit, used by every integration test
that touches the ledger and available to the console for a future
integrity view.

## Not yet built

The React console and everything under `bench/`/`demo/` all exist and
work (Phase 4/5). What's genuinely not implemented: Tier 2 deep
verification, and a production deployment topology (this describes one
gateway process + one console process against one database — no load
balancing, no multi-region, no Redis-backed shared state for the cost
breaker). See `docs/assumptions.md` for the full list.
