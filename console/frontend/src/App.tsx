import { useEffect, useState, useCallback } from "react";
import { api } from "./api";
import type { Summary, EventRow, EventDetail } from "./types";
import { SummaryCards } from "./components/SummaryCards";
import { DecisionBars } from "./components/DecisionBars";
import { EventsTable } from "./components/EventsTable";
import { EventDetailDrawer } from "./components/EventDetailDrawer";
import { RiskAppetiteControl } from "./components/RiskAppetiteControl";
import { HumanFeedbackPanel } from "./components/HumanFeedbackPanel";

const PAGE_SIZE = 25;

export default function App() {
  const [tenants, setTenants] = useState<string[]>([]);
  const [tenant, setTenant] = useState<string>("");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [events, setEvents] = useState<EventRow[]>([]);
  const [offset, setOffset] = useState(0);
  const [detail, setDetail] = useState<EventDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [feedbackRefreshKey, setFeedbackRefreshKey] = useState(0);

  const refresh = useCallback(async () => {
    try {
      const [s, e] = await Promise.all([
        api.summary(tenant || undefined),
        api.events({ tenant: tenant || undefined, limit: PAGE_SIZE, offset }),
      ]);
      setSummary(s);
      setEvents(e);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [tenant, offset]);

  useEffect(() => {
    api.tenants().then(setTenants).catch(() => setTenants([]));
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, [refresh]);

  useEffect(() => {
    setOffset(0);
  }, [tenant]);

  async function openDetail(requestId: string) {
    try {
      setDetail(await api.eventDetail(requestId));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function refreshOpenDetail() {
    if (detail) await openDetail(detail.request.request_id);
    setFeedbackRefreshKey((k) => k + 1);
  }

  return (
    <>
      <header>
        <div>
          <h1>ControlPlane Console</h1>
          <p>Live view over the audit ledger — auto-refreshes every 5s.</p>
        </div>
        <select value={tenant} onChange={(e) => setTenant(e.target.value)}>
          <option value="">All tenants</option>
          {tenants.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </header>

      {error && (
        <div className="error-banner">
          Could not reach the console API: {error}. Is console/backend running?
        </div>
      )}

      <SummaryCards summary={summary} />

      {tenant && <RiskAppetiteControl tenant={tenant} />}
      {tenant && <HumanFeedbackPanel tenant={tenant} refreshKey={feedbackRefreshKey} />}

      <div className="panel">
        <h2>Decisions</h2>
        <DecisionBars counts={summary?.decision_counts ?? {}} />
      </div>

      <div className="panel">
        <h2>Recent requests</h2>
        <EventsTable events={events} onSelect={openDetail} />
        <div className="pager">
          <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
            Previous
          </button>
          <button disabled={events.length < PAGE_SIZE} onClick={() => setOffset(offset + PAGE_SIZE)}>
            Next
          </button>
        </div>
      </div>

      <EventDetailDrawer detail={detail} onClose={() => setDetail(null)} onReviewSubmitted={refreshOpenDetail} />
    </>
  );
}
