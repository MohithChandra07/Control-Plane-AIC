import type { Summary, EventRow, EventDetail, RiskAppetite, HumanAgreement, Recalibration } from "./types";

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) {
    throw new Error(`${path} -> HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}

async function writeJSON<T>(method: "PUT" | "POST", path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
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

  riskAppetite: (tenant: string) => getJSON<RiskAppetite>(`/api/risk-appetite/${encodeURIComponent(tenant)}`),

  setRiskAppetite: (tenant: string, riskAppetite: number, updatedBy?: string) =>
    writeJSON<RiskAppetite>("PUT", `/api/risk-appetite/${encodeURIComponent(tenant)}`, {
      risk_appetite: riskAppetite,
      updated_by: updatedBy ?? null,
    }),

  submitReview: (opts: { requestId: string; claimId?: string | null; reviewer: string; agree: boolean; notes?: string }) =>
    writeJSON<{ status: string }>("POST", "/api/reviews", {
      request_id: opts.requestId,
      claim_id: opts.claimId ?? null,
      reviewer: opts.reviewer,
      agree: opts.agree,
      notes: opts.notes ?? null,
    }),

  humanAgreement: (tenant: string) => getJSON<HumanAgreement>(`/api/human-agreement/${encodeURIComponent(tenant)}`),

  recalibration: (tenant: string) => getJSON<Recalibration>(`/api/recalibration/${encodeURIComponent(tenant)}`),
};
