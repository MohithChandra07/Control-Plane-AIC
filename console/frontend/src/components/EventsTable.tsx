import { useState } from "react";
import type { EventRow } from "../types";

export function EventsTable({
  events,
  onSelect,
}: {
  events: EventRow[];
  onSelect: (requestId: string) => void;
}) {
  const [search, setSearch] = useState("");
  const [filterDecision, setFilterDecision] = useState<string>("ALL");

  const filtered = events.filter((e) => {
    const matchesDecision = filterDecision === "ALL" || e.decision === filterDecision;
    const matchesSearch =
      !search ||
      e.request_id.toLowerCase().includes(search.toLowerCase()) ||
      e.tenant_id.toLowerCase().includes(search.toLowerCase()) ||
      (e.conversation_id && e.conversation_id.toLowerCase().includes(search.toLowerCase()));
    return matchesDecision && matchesSearch;
  });

  return (
    <div>
      <div className="table-toolbar">
        <input
          type="text"
          className="search-input"
          placeholder="🔍 Search request ID, tenant, conversation..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="filter-tabs">
          {["ALL", "ALLOW", "MODIFY", "ESCALATE", "BLOCK"].map((d) => (
            <button
              key={d}
              className={`filter-tab ${filterDecision === d ? "active" : ""}`}
              onClick={() => setFilterDecision(d)}
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="empty">No audit ledger entries match your filter.</div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Tenant</th>
              <th>Decision</th>
              <th>Latency</th>
              <th>Request ID</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((e) => (
              <tr key={e.request_id} className="clickable" onClick={() => onSelect(e.request_id)}>
                <td style={{ color: "var(--text-dim)", fontSize: 12 }}>
                  {new Date(e.created_at).toLocaleTimeString()}
                </td>
                <td style={{ fontWeight: 600 }}>{e.tenant_id}</td>
                <td>
                  <span className={`badge badge-${e.decision}`}>{e.decision}</span>
                </td>
                <td style={{ color: "var(--text-dim)", fontVariantNumeric: "tabular-nums" }}>
                  {e.latency_ms !== null ? `${e.latency_ms.toFixed(1)} ms` : "—"}
                </td>
                <td className="mono" title={e.request_id} style={{ color: "var(--primary)" }}>
                  {e.request_id.slice(0, 16)}…
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
