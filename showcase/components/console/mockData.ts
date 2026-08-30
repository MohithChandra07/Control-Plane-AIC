export type Decision = "ALLOW" | "MODIFY" | "ESCALATE" | "BLOCK";
export type ClaimVerdict = "SUPPORTED" | "CONTRADICTED" | "UNVERIFIED";

export type ConsoleRequest = {
  requestId: string;
  tenant: string;
  turn: number;
  decision: Decision;
  latency: number;
  time: string;
  claims: {
    id: string;
    text: string;
    verdict: ClaimVerdict;
    risk: string[];
    taint: "clean" | "tainted";
    remediation: Decision;
  }[];
  tools: { name: string; action: string; remediation: Decision; provenance: string; taint: string }[];
  metadata: { model: string; tier: string; tokens: number; cost: string; policy: string };
};

const tenants = ["customer_support", "regulated_agent", "internal_copilot"];
const decisions: Decision[] = ["ALLOW", "MODIFY", "ESCALATE", "BLOCK"];
const base: Record<string, number> = { ALLOW: 3533, MODIFY: 3429, ESCALATE: 2701, BLOCK: 337 };

const claimTemplates = [
  { id: "claim-refund-window", text: "Refunds are available within 43 days of purchase.", verdict: "CONTRADICTED" as const, risk: ["hallucination", "policy"], taint: "tainted" as const, remediation: "ESCALATE" as Decision },
  { id: "claim-identity-check", text: "The account can be updated after identity verification.", verdict: "SUPPORTED" as const, risk: [], taint: "clean" as const, remediation: "ALLOW" as Decision },
  { id: "claim-card-number", text: "The customer should share their full card number in chat.", verdict: "UNVERIFIED" as const, risk: ["pii", "policy"], taint: "tainted" as const, remediation: "BLOCK" as Decision },
  { id: "claim-order-status", text: "I can check the order status using the support tool.", verdict: "SUPPORTED" as const, risk: [], taint: "clean" as const, remediation: "ALLOW" as Decision },
];

export const MOCK_REQUESTS: ConsoleRequest[] = Array.from({ length: 50 }, (_, i) => {
  const tenant = tenants[i % tenants.length];
  const decision = decisions[(i * 7 + Math.floor(i / 3)) % decisions.length];
  const claim = claimTemplates[i % claimTemplates.length];
  const hasTool = i % 4 === 0 || i % 7 === 0;
  return {
    requestId: `26c0f137-${String(i + 1).padStart(4, "0")}-4b93-ab8b-d456-a7df${String(7920 + i).padStart(4, "0")}`,
    tenant,
    turn: (i % 5) + 1,
    decision,
    latency: Number((6.2 + ((i * 17) % 31) / 10).toFixed(1)),
    time: `11:${String(50 - Math.floor(i / 10)).padStart(2, "0")}:${String(34 - (i % 10)).padStart(2, "0")} AM`,
    claims: i % 3 === 0 ? [claim] : [],
    tools: hasTool ? [{ name: "lookup_order", action: '{"order_id":"ORD-84291"}', remediation: decision === "BLOCK" ? "BLOCK" : "ALLOW", provenance: "support.orders.v2", taint: decision === "BLOCK" ? "tainted" : "clean" }] : [],
    metadata: { model: i % 2 ? "gpt-4.1-mini" : "gpt-4.1", tier: i % 3 ? "Tier 0 → Tier 1" : "Tier 0", tokens: 640 + i * 11, cost: `$${(0.004 + i * 0.00007).toFixed(4)}`, policy: `${tenant}.yaml` },
  };
});

export function summaryFor(tenant?: string) {
  const rows = tenant ? MOCK_REQUESTS.filter((r) => r.tenant === tenant) : MOCK_REQUESTS;
  const counts = rows.reduce<Record<Decision, number>>((acc, r) => { acc[r.decision] += 1; return acc; }, { ALLOW: 0, MODIFY: 0, ESCALATE: 0, BLOCK: 0 });
  return {
    total: tenant ? 50 : 10000,
    counts: tenant ? counts : base,
    escalation: tenant ? (counts.ESCALATE / Math.max(rows.length, 1)) * 100 : 27.0,
    p50: tenant ? 1.4 + (tenants.indexOf(tenant) * 0.3) : 7.0,
    p95: tenant ? 2.1 + (tenants.indexOf(tenant) * 0.35) : 8.4,
  };
}
