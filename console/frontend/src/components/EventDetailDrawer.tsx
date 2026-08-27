import type { EventDetail } from "../types";

export function EventDetailDrawer({
  detail,
  onClose,
}: {
  detail: EventDetail | null;
  onClose: () => void;
}) {
  if (!detail) return null;

  return (
    <div className="overlay" onClick={onClose}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        <h3>Request {detail.request.request_id}</h3>
        <p style={{ color: "var(--text-dim)", fontSize: 13 }}>
          {detail.request.tenant_id} · turn {detail.request.turn_id ?? "—"} ·{" "}
          <span className={`badge badge-${detail.request.decision}`}>{detail.request.decision}</span>
        </p>
        {detail.request.error && <div className="error-banner">{detail.request.error}</div>}

        <h4>Claims ({detail.claims.length})</h4>
        {detail.claims.length === 0 && <div className="empty">No claims extracted (Tier 0 only).</div>}
        {detail.claims.map((c) => (
          <div className="claim-card" key={c.claim_id}>
            <div>
              <span className={`badge badge-${c.remediation ?? "ALLOW"}`}>{c.remediation ?? "ALLOW"}</span>{" "}
              <strong>{c.verdict}</strong>
              {c.taint_status === "tainted" && <span className="risk-tag" style={{ marginLeft: 6 }}>tainted</span>}
            </div>
            <div className="claim-text">{c.claim_text}</div>
            <div className="risk-tags">
              {c.risk_labels &&
                Object.entries(c.risk_labels)
                  .filter(([, v]) => v.evaluated && v.detected)
                  .map(([label]) => (
                    <span className="risk-tag" key={label}>
                      {label}
                    </span>
                  ))}
            </div>
          </div>
        ))}

        <h4>Tool calls ({detail.tool_calls.length})</h4>
        {detail.tool_calls.length === 0 && <div className="empty">No tool calls in this response.</div>}
        {detail.tool_calls.map((t, i) => (
          <div className="claim-card" key={i}>
            <span className={`badge badge-${t.remediation ?? "ALLOW"}`}>{t.remediation ?? "ALLOW"}</span>
            <pre style={{ fontSize: 12, whiteSpace: "pre-wrap", marginTop: 8 }}>
              {JSON.stringify(t.action, null, 2)}
            </pre>
          </div>
        ))}

        <button onClick={onClose} style={{ marginTop: 12 }}>
          Close
        </button>
      </div>
    </div>
  );
}
