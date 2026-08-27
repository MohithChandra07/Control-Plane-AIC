import type { Summary, EventRow, EventDetail } from "./types";

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) {
    throw new Error(`${path} -> HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}

export const api = {
  tenants: () => getJSON<string[]>("/api/tenants"),

  summary: (tenant?: string) =>
    getJSON<Summary>(`/api/summary${tenant ? `?tenant=${encodeURIComponent(tenant)}` : ""}`),

  events: (opts: { tenant?: string; decision?: string; limit?: number; offset?: number }) => {
    const params = new URLSearchParams();
    if (opts.tenant) params.set("tenant", opts.tenant);
    if (opts.decision) params.set("decision", opts.decision);
    params.set("limit", String(opts.limit ?? 50));
    params.set("offset", String(opts.offset ?? 0));
    return getJSON<EventRow[]>(`/api/events?${params.toString()}`);
  },

  eventDetail: (requestId: string) => getJSON<EventDetail>(`/api/events/${encodeURIComponent(requestId)}`),
};
