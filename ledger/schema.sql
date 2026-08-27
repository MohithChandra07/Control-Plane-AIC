-- ControlPlane audit ledger schema (Postgres).
-- Mirrors ledger/models.py:AuditEvent. Applied automatically by
-- docker-compose (postgres init script); SQLAlchemy's init_models() is used
-- for tests/local dev against sqlite instead.

CREATE TABLE IF NOT EXISTS audit_events (
    id              BIGSERIAL PRIMARY KEY,
    request_id      VARCHAR(64) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    kind            VARCHAR(16) NOT NULL DEFAULT 'request',

    tenant_id       VARCHAR(64) NOT NULL,
    conversation_id VARCHAR(64),
    turn_id         INTEGER,

    claim_id        VARCHAR(64),
    claim_text      TEXT,
    verdict         VARCHAR(32),
    risk_labels     JSONB,
    provenance      JSONB,
    taint_status    VARCHAR(32),
    remediation     VARCHAR(32),

    action          JSONB,

    policy_name     VARCHAR(64) NOT NULL,
    decision        VARCHAR(32) NOT NULL,
    latency_ms      DOUBLE PRECISION,
    error           TEXT,

    prev_hash       VARCHAR(64) NOT NULL,
    hash            VARCHAR(64) NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS ix_audit_events_request_id ON audit_events (request_id);
CREATE INDEX IF NOT EXISTS ix_audit_events_tenant_id ON audit_events (tenant_id);
CREATE INDEX IF NOT EXISTS ix_audit_events_hash ON audit_events (hash);
CREATE INDEX IF NOT EXISTS ix_audit_events_conversation_id ON audit_events (conversation_id);
CREATE INDEX IF NOT EXISTS ix_audit_events_kind ON audit_events (kind);
