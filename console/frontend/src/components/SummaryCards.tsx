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
        <div className="label">Total requests</div>
        <div className="value">{summary ? summary.total_requests : "—"}</div>
      </div>
      <div className="card">
        <div className="label">Escalation rate</div>
        <div className="value">{summary ? fmtPct(summary.escalation_rate) : "—"}</div>
      </div>
      <div className="card">
        <div className="label">p50 latency</div>
        <div className="value">{summary ? fmtMs(summary.latency_ms.p50) : "—"}</div>
      </div>
      <div className="card">
        <div className="label">p95 latency</div>
        <div className="value">{summary ? fmtMs(summary.latency_ms.p95) : "—"}</div>
      </div>
    </div>
  );
}
