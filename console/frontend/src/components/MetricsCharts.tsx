import type { Summary } from "../types";

interface Props {
  summary: Summary | null;
}

export function MetricsCharts({ summary }: Props) {
  if (!summary) return null;

  const counts = summary.decision_counts || {};
  const total = summary.total_requests || 1;

  const allowPct = Math.round(((counts.ALLOW || 0) / total) * 100);
  const modifyPct = Math.round(((counts.MODIFY || 0) / total) * 100);
  const escalatePct = Math.round(((counts.ESCALATE || 0) / total) * 100);
  const blockPct = Math.round(((counts.BLOCK || 0) / total) * 100);

  const p50 = summary.latency_ms.p50 ? summary.latency_ms.p50.toFixed(2) : "N/A";
  const p95 = summary.latency_ms.p95 ? summary.latency_ms.p95.toFixed(2) : "N/A";

  return (
    <div className="panel visual-analytics-panel">
      <h2>Visual Analytics & System Health</h2>
      <div className="charts-grid">
        {/* Latency Gauge */}
        <div className="chart-card">
          <h3>Latency Distribution</h3>
          <div className="gauge-container">
            <div className="metric-pill p50">
              <span className="label">p50 Latency</span>
              <span className="value">{p50} ms</span>
            </div>
            <div className="metric-pill p95">
              <span className="label">p95 Latency</span>
              <span className="value">{p95} ms</span>
            </div>
          </div>
          <p className="chart-footnote">Adaptive scrutiny keeps p50 latency minimal for low-risk traffic.</p>
        </div>

        {/* Decision Breakdown Proportions */}
        <div className="chart-card">
          <h3>Decision Share</h3>
          <div className="progress-stacked">
            <div style={{ width: `${allowPct}%`, backgroundColor: "#22c55e" }} title={`ALLOW: ${allowPct}%`} />
            <div style={{ width: `${modifyPct}%`, backgroundColor: "#eab308" }} title={`MODIFY: ${modifyPct}%`} />
            <div style={{ width: `${escalatePct}%`, backgroundColor: "#f97316" }} title={`ESCALATE: ${escalatePct}%`} />
            <div style={{ width: `${blockPct}%`, backgroundColor: "#ef4444" }} title={`BLOCK: ${blockPct}%`} />
          </div>
          <div className="chart-legend">
            <span><strong style={{ color: "#22c55e" }}>■</strong> ALLOW ({allowPct}%)</span>
            <span><strong style={{ color: "#eab308" }}>■</strong> MODIFY ({modifyPct}%)</span>
            <span><strong style={{ color: "#f97316" }}>■</strong> ESCALATE ({escalatePct}%)</span>
            <span><strong style={{ color: "#ef4444" }}>■</strong> BLOCK ({blockPct}%)</span>
          </div>
        </div>

        {/* Evaluated Risk Vectors */}
        <div className="chart-card">
          <h3>Evaluated Risk Dimensions</h3>
          <ul className="risk-pillars">
            <li><span className="pillar-name">Hallucination</span> <span className="pillar-badge active">100% Evaluated</span></li>
            <li><span className="pillar-name">PII & Secrets</span> <span className="pillar-badge active">100% Evaluated</span></li>
            <li><span className="pillar-name">Toxicity</span> <span className="pillar-badge active">100% Evaluated</span></li>
            <li><span className="pillar-name">Demographic Bias</span> <span className="pillar-badge active">100% Evaluated</span></li>
            <li><span className="pillar-name">Policy Violation</span> <span className="pillar-badge active">100% Evaluated</span></li>
          </ul>
        </div>
      </div>
    </div>
  );
}
