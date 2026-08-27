import { useEffect, useState } from "react";
import { api } from "../api";
import type { RiskAppetite } from "../types";

export function RiskAppetiteControl({ tenant }: { tenant: string }) {
  const [appetite, setAppetite] = useState<RiskAppetite | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setAppetite(null);
    api.riskAppetite(tenant).then(setAppetite).catch((e) => setError(String(e)));
  }, [tenant]);

  async function commit(value: number) {
    setPending(true);
    try {
      const updated = await api.setRiskAppetite(tenant, value, "console-user");
      setAppetite({ ...updated, updated_at: new Date().toISOString() });
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setPending(false);
    }
  }

  if (!appetite) return null;

  const label =
    appetite.risk_appetite < 0.35 ? "Permissive" : appetite.risk_appetite > 0.65 ? "Strict" : "Balanced (default)";

  return (
    <div className="panel">
      <h2>Risk appetite — {tenant}</h2>
      <p style={{ color: "var(--text-dim)", fontSize: 13, marginTop: -6 }}>
        Scales this tenant's own Tier 0/1 scrutiny thresholds relative to their configured
        baseline. Not cosmetic — moves real detection recall, escalation rate, and latency; see{" "}
        <code>bench/harness/run_appetite_sweep.py</code>.
      </p>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 8 }}>
        <span style={{ fontSize: 12, color: "var(--text-dim)" }}>Permissive</span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={appetite.risk_appetite}
          disabled={pending}
          onChange={(e) => setAppetite({ ...appetite, risk_appetite: Number(e.target.value) })}
          onMouseUp={(e) => commit(Number((e.target as HTMLInputElement).value))}
          onTouchEnd={(e) => commit(Number((e.target as HTMLInputElement).value))}
          style={{ flex: 1 }}
        />
        <span style={{ fontSize: 12, color: "var(--text-dim)" }}>Strict</span>
        <strong style={{ minWidth: 130, textAlign: "right" }}>
          {appetite.risk_appetite.toFixed(2)} · {label}
        </strong>
      </div>
      {appetite.updated_by && (
        <p style={{ color: "var(--text-dim)", fontSize: 12, marginTop: 8 }}>
          Last changed by {appetite.updated_by}
          {appetite.updated_at ? ` at ${new Date(appetite.updated_at).toLocaleString()}` : ""}.
        </p>
      )}
      {error && <div className="error-banner">{error}</div>}
    </div>
  );
}
