import type { EventRow } from "../types";

export function EventsTable({
  events,
  onSelect,
}: {
  events: EventRow[];
  onSelect: (requestId: string) => void;
}) {
  if (events.length === 0) {
    return <div className="empty">No events for this filter.</div>;
  }

  return (
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
        {events.map((e) => (
          <tr key={e.request_id} className="clickable" onClick={() => onSelect(e.request_id)}>
            <td>{new Date(e.created_at).toLocaleTimeString()}</td>
            <td>{e.tenant_id}</td>
            <td>
              <span className={`badge badge-${e.decision}`}>{e.decision}</span>
            </td>
            <td>{e.latency_ms !== null ? `${e.latency_ms.toFixed(1)} ms` : "—"}</td>
            <td title={e.request_id}>{e.request_id.slice(0, 8)}…</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
