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

## Repo layout (as of Phase 2)

```
gateway/    FastAPI app, OpenAI-compatible routes, provider abstraction
policy/     Policy schema (Pydantic) + YAML loader + governance engine (engine.py)
detectors/  Claim extraction, Tier 0 gate, PII detector, heuristic claim verifier
data/       corpus/ — small fake enterprise docs the claim verifier grounds against
ledger/     SQLAlchemy audit models, hash-chained writer, Postgres schema
configs/    One YAML policy per tenant
tests/      unit/ (no I/O) and integration/ (async DB + TestClient)
```

Directories from the target structure (`bench/`, `demo/`, `console/`, etc.)
are created when the phase that needs them starts, not before — see
`docs/roadmap.md`.

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
