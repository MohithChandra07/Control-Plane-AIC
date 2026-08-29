import type { Summary } from "../types";

function fmtMs(v: number | null): string {
  return v === null ? "—" : `${v.toFixed(1)} ms`;
}

function fmtPct(v: number | null): string {
  return v === null ? "—" : `${(v * 100).toFixed(1)}%`;
}

export function SummaryCards({ summary }: { summary: Summary | null }) {
  return (
    <div className="cards">
      <div className="card">
        <div className="label">
          <span>Total Interactions</span>
          <span>⚡ Live</span>
        </div>
        <div className="value">{summary ? summary.total_requests.toLocaleString() : "—"}</div>
        <div className="subtext">Audited via hash-chain</div>
      </div>
      <div className="card">
        <div className="label">
          <span>Escalation Rate</span>
          <span>🛡️ Gated</span>
        </div>
        <div className="value" style={{ color: "var(--escalate)" }}>
          {summary ? fmtPct(summary.escalation_rate) : "—"}
        </div>
        <div className="subtext">Requires human verification</div>
      </div>
      <div className="card">
        <div className="label">
          <span>p50 Latency</span>
          <span>🚀 Tier 0</span>
        </div>
        <div className="value" style={{ color: "var(--allow)" }}>
          {summary ? fmtMs(summary.latency_ms.p50) : "—"}
        </div>
        <div className="subtext">Micro-scrutiny baseline</div>
      </div>
      <div className="card">
        <div className="label">
          <span>p95 Latency</span>
          <span>🔍 Tier 1</span>
        </div>
        <div className="value" style={{ color: "var(--modify)" }}>
          {summary ? fmtMs(summary.latency_ms.p95) : "—"}
        </div>
        <div className="subtext">Deep verification ceiling</div>
      </div>
    </div>
  );
}
