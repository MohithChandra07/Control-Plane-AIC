const COLORS: Record<string, string> = {
  ALLOW: "var(--allow)",
  MODIFY: "var(--modify)",
  ESCALATE: "var(--escalate)",
  BLOCK: "var(--block)",
  ERROR: "var(--error)",
};

const ORDER = ["ALLOW", "MODIFY", "ESCALATE", "BLOCK", "ERROR"];

export function DecisionBars({ counts }: { counts: Record<string, number> }) {
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  const keys = ORDER.filter((k) => counts[k] !== undefined).concat(
    Object.keys(counts).filter((k) => !ORDER.includes(k))
  );

  if (total === 0) {
    return <div className="empty">No requests yet — run the replayer or send traffic through the gateway.</div>;
  }

  return (
    <div className="decision-bars">
      {keys.map((key) => {
        const count = counts[key] ?? 0;
        const pct = total ? (count / total) * 100 : 0;
        return (
          <div className="decision-bar-row" key={key}>
            <span>{key}</span>
            <div className="decision-bar-track">
              <div
                className="decision-bar-fill"
                style={{ width: `${pct}%`, background: COLORS[key] ?? "var(--text-dim)" }}
              />
            </div>
            <span>{count}</span>
          </div>
        );
      })}
    </div>
  );
}
