"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Database,
  Github,
  Layers,
  RefreshCw,
  ScrollText,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Timer,
  Users,
  Wifi,
  WifiOff,
  X,
} from "lucide-react";
import { MOCK_REQUESTS, summaryFor, type ConsoleRequest, type Decision } from "./mockData";
import { consoleApi, type LiveEventDetail, type LivePolicy } from "@/lib/api";
import { APPETITE_SOURCE, APPETITE_SWEEP, BENCH_SOURCE, SCRUTINY_MODES } from "@/lib/telemetry";

const TENANTS = ["customer_support", "regulated_agent", "internal_copilot"];
const DECISIONS: Decision[] = ["ALLOW", "MODIFY", "ESCALATE", "BLOCK"];

const decisionMeta: Record<string, { label: string; className: string }> = {
  ALLOW: { label: "ALLOW", className: "cp-allow" },
  MODIFY: { label: "MODIFY", className: "cp-modify" },
  ESCALATE: { label: "ESCALATE", className: "cp-escalate" },
  BLOCK: { label: "BLOCK", className: "cp-block" },
};

/**
 * The real configs/*.yaml, transcribed for the moment the console backend
 * (:8001, GET /api/policies) isn't reachable — same values, not invented.
 * Kept in sync with configs/customer_support.yaml, configs/internal_copilot.yaml
 * and configs/regulated_agent.yaml.
 */
const FALLBACK_POLICIES: LivePolicy[] = [
  {
    tenant_id: "customer_support",
    display_name: "Customer Support Assistant",
    description:
      "Customer-facing chatbot. Conservative posture: unverifiable claims are hedged rather than stated as fact, PII is redacted by default, and the system fails closed on detector failure.",
    latency_budget_ms: 150,
    unverifiable_handling: "HEDGE",
    risk_thresholds: { tier1_trigger: 0.3, tier2_trigger: 0.6, block_trigger: 0.85 },
    pii: { enabled: true, remediation: "REDACT", hard_block_categories: ["credit_card", "government_id"] },
    tool_calls: { enabled: false, consequential_sinks: [], tainted_argument_action: "BLOCK", require_verified_provenance: true },
    escalation: { enabled: true, max_escalation_rate: 0.15 },
    cost_breaker: { enabled: true, window_seconds: 60, max_requests_per_window: 30, max_tokens_per_window: 20000 },
    model_routing: { enabled: true, cheap_model: "gpt-4o-mini", escalation_model: "gpt-4o" },
    fail_mode: "fail_closed",
  },
  {
    tenant_id: "internal_copilot",
    display_name: "Internal Knowledge Copilot",
    description:
      "Internal-facing assistant for employees. More tolerant of unverifiable claims (hedged, rarely blocked) since the audience can independently verify against internal systems. Still redacts PII.",
    latency_budget_ms: 600,
    unverifiable_handling: "ALLOW",
    risk_thresholds: { tier1_trigger: 0.5, tier2_trigger: 0.8, block_trigger: 0.95 },
    pii: { enabled: true, remediation: "REDACT", hard_block_categories: ["credit_card", "government_id"] },
    tool_calls: { enabled: false, consequential_sinks: [], tainted_argument_action: "ESCALATE", require_verified_provenance: false },
    escalation: { enabled: true, max_escalation_rate: 0.3 },
    cost_breaker: { enabled: true, window_seconds: 60, max_requests_per_window: 120, max_tokens_per_window: 200000 },
    model_routing: { enabled: true, cheap_model: "gpt-4o-mini", escalation_model: "gpt-4o" },
    fail_mode: "fail_open",
  },
  {
    tenant_id: "regulated_agent",
    display_name: "Regulated Decision-Support Agent",
    description:
      "Agent with consequential tool access (e.g. issuing refunds). Strongest verification requirements: unverifiable claims used as tool-call arguments are blocked, not just hedged, and any tainted argument to a consequential sink is blocked. Fails closed everywhere.",
    latency_budget_ms: 2000,
    unverifiable_handling: "ESCALATE",
    risk_thresholds: { tier1_trigger: 0.2, tier2_trigger: 0.4, block_trigger: 0.7 },
    pii: { enabled: true, remediation: "REDACT", hard_block_categories: ["credit_card", "government_id", "bank_account"] },
    tool_calls: {
      enabled: true,
      consequential_sinks: ["money_movement", "database_write", "external_communication"],
      tainted_argument_action: "BLOCK",
      require_verified_provenance: true,
    },
    escalation: { enabled: true, max_escalation_rate: 0.4 },
    cost_breaker: { enabled: true, window_seconds: 60, max_requests_per_window: 20, max_tokens_per_window: 50000 },
    model_routing: { enabled: false, cheap_model: "gpt-4o-mini", escalation_model: "gpt-4o" },
    fail_mode: "fail_closed",
  },
];

type Tab = "overview" | "interactions" | "policy" | "scrutiny" | "review";
type Mode = "checking" | "live" | "demo";

interface Row {
  requestId: string;
  tenant: string;
  decision: string;
  latency: number;
  time: string;
}

function Badge({ decision }: { decision: string }) {
  const m = decisionMeta[decision] ?? { label: decision, className: "" };
  return <span className={`cp-badge ${m.className}`}>{m.label}</span>;
}

/** Small grouped/vertical bar chart — plain SVG, no charting lib, consistent
 * with the landing page's hand-rolled charts (components/sections/Console.tsx). */
function MiniBarChart({
  groups,
  height = 120,
}: {
  groups: { label: string; bars: { value: number; color: string; caption: string }[] }[];
  height?: number;
}) {
  const barWidth = 14;
  const barGap = 4;
  const groupGap = 22;
  const groupWidth = groups[0] ? groups[0].bars.length * (barWidth + barGap) : 0;
  const width = groups.length * groupWidth + (groups.length - 1) * groupGap + 16;
  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} role="img" aria-label="bar chart">
      {groups.map((g, gi) => {
        const gx = 8 + gi * (groupWidth + groupGap);
        return (
          <g key={g.label}>
            {g.bars.map((b, bi) => {
              const barH = Math.max(b.value * (height - 24), 2);
              const bx = gx + bi * (barWidth + barGap);
              return (
                <g key={bi}>
                  <title>{b.caption}</title>
                  <rect x={bx} y={height - 20 - barH} width={barWidth} height={barH} rx={2} fill={b.color} />
                </g>
              );
            })}
            <text x={gx + groupWidth / 2 - barGap} y={height - 5} textAnchor="middle" fontSize={9} fontFamily="var(--font-mono)" fill="#6f7d94">
              {g.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/** Small sparkline — one series, no axes, just shape. */
function MiniLineChart({ values, color, height = 90 }: { values: number[]; color: string; height?: number }) {
  const width = 280;
  const padY = 10;
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = Math.max(max - min, 0.001);
  const stepX = values.length > 1 ? (width - 16) / (values.length - 1) : 0;
  const y = (v: number) => height - padY - ((v - min) / range) * (height - padY * 2);
  const path = values.map((v, i) => `${i === 0 ? "M" : "L"}${(8 + i * stepX).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} role="img" aria-label="line chart">
      <path d={path} fill="none" stroke={color} strokeWidth={1.8} />
      {values.map((v, i) => (
        <circle key={i} cx={8 + i * stepX} cy={y(v)} r={2} fill={color} />
      ))}
    </svg>
  );
}

function Panel({ title, children, right }: { title: string; children: React.ReactNode; right?: React.ReactNode }) {
  return (
    <section className="cp-panel">
      <div className="cp-panel-head">
        <h2>{title}</h2>
        {right}
      </div>
      {children}
    </section>
  );
}

export function ConsoleApp() {
  const [mode, setMode] = useState<Mode>("checking");
  const [probeError, setProbeError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("overview");
  const [tenant, setTenant] = useState("");
  const [tenants, setTenants] = useState<string[]>(TENANTS);
  const [policies, setPolicies] = useState<LivePolicy[]>(FALLBACK_POLICIES);

  const [demoRequests, setDemoRequests] = useState(MOCK_REQUESTS);
  const [liveRows, setLiveRows] = useState<Row[] | null>(null);
  const [liveSummary, setLiveSummary] = useState<{
    total: number;
    counts: Record<Decision, number>;
    escalation: number;
    p50: number;
    p95: number;
  } | null>(null);

  const [page, setPage] = useState(0);
  const [query, setQuery] = useState("");
  const [decisionFilter, setDecisionFilter] = useState("");
  // Starts null rather than `new Date()`: this page is statically prerendered,
  // and a timestamp baked in at build time would never match the client's
  // clock on hydration (React error #418). Set for real once mounted.
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  useEffect(() => setLastUpdate(new Date()), []);

  const [selectedRow, setSelectedRow] = useState<Row | null>(null);
  const [selectedMock, setSelectedMock] = useState<ConsoleRequest | null>(null);
  const [selectedDetail, setSelectedDetail] = useState<LiveEventDetail | null>(null);
  const [expandedTools, setExpandedTools] = useState(false);

  const [risk, setRisk] = useState(0.5);
  const [riskSaving, setRiskSaving] = useState(false);
  const [riskSavedNote, setRiskSavedNote] = useState<string | null>(null);

  const [reviewed, setReviewed] = useState<Record<string, boolean>>({});
  const [agreement, setAgreement] = useState<{ count: number; rate: number | null }>({ count: 0, rate: null });
  const [recalibration, setRecalibration] = useState<{
    reviewed_count: number;
    disagreement_rate: number;
    suggested_appetite_delta: number;
    message: string;
  } | null>(null);
  const [liveReviews, setLiveReviews] = useState<
    { created_at: string; reviewed_request_id?: string; reviewer?: string; agree?: boolean }[]
  >([]);

  const [probeAttempt, setProbeAttempt] = useState(0);
  function retryProbe() {
    setMode("checking");
    setProbeError(null);
    setProbeAttempt((n) => n + 1);
  }

  // Probe the real console backend on mount, and again whenever retryProbe()
  // is called. A static showcase deploy usually has nothing on :8001, so
  // this settles into "demo" within ~3s unless retried.
  useEffect(() => {
    let cancelled = false;
    consoleApi
      .tenants()
      .then((t) => {
        if (cancelled) return;
        setMode("live");
        setProbeError(null);
        if (t.length) setTenants(t);
        consoleApi.policies().then((p) => !cancelled && p.length && setPolicies(p)).catch(() => {});
      })
      .catch((err) => {
        if (cancelled) return;
        setMode("demo");
        setProbeError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [probeAttempt]);

  useEffect(() => {
    if (mode !== "live") return;
    let cancelled = false;
    consoleApi
      .summary(tenant || undefined)
      .then((s) => {
        if (cancelled) return;
        setLiveSummary({
          total: s.total_requests,
          counts: {
            ALLOW: s.decision_counts.ALLOW ?? 0,
            MODIFY: s.decision_counts.MODIFY ?? 0,
            ESCALATE: s.decision_counts.ESCALATE ?? 0,
            BLOCK: s.decision_counts.BLOCK ?? 0,
          },
          escalation: (s.escalation_rate ?? 0) * 100,
          p50: s.latency_ms.p50 ?? 0,
          p95: s.latency_ms.p95 ?? 0,
        });
      })
      .catch(() => {});
    consoleApi
      .events({ tenant: tenant || undefined, decision: decisionFilter || undefined, limit: 10, offset: page * 10 })
      .then(
        (events) =>
          !cancelled &&
          setLiveRows(
            events.map((e) => ({
              requestId: e.request_id,
              tenant: e.tenant_id,
              decision: e.decision,
              latency: e.latency_ms ?? 0,
              time: new Date(e.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
            }))
          )
      )
      .catch(() => !cancelled && setLiveRows([]));
    return () => {
      cancelled = true;
    };
  }, [mode, tenant, page, decisionFilter, lastUpdate]);

  useEffect(() => {
    if (mode !== "live" || !tenant) return;
    let cancelled = false;
    consoleApi.riskAppetite(tenant).then((r) => !cancelled && setRisk(r.risk_appetite)).catch(() => {});
    consoleApi
      .humanAgreement(tenant)
      .then((r) => !cancelled && setAgreement({ count: r.reviewed_count, rate: r.agreement_rate }))
      .catch(() => {});
    consoleApi.recalibration(tenant).then((r) => !cancelled && setRecalibration(r.suggestion)).catch(() => {});
    consoleApi.listReviews(tenant).then((r) => !cancelled && setLiveReviews(r)).catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [mode, tenant]);

  useEffect(() => {
    if (mode !== "demo") return;
    const id = window.setInterval(() => {
      setDemoRequests((rows) =>
        rows.map((r, i) => (i < 10 ? { ...r, latency: Number(Math.max(5.8, r.latency + (((Date.now() + i) % 7) - 3) * 0.1).toFixed(1)) } : r))
      );
      setLastUpdate(new Date());
    }, 5000);
    return () => window.clearInterval(id);
  }, [mode]);

  const demoSummary = summaryFor(tenant || undefined);
  const filteredDemo = useMemo(
    () =>
      demoRequests.filter(
        (r) =>
          (!tenant || r.tenant === tenant) &&
          (!query || `${r.requestId} ${r.tenant} ${r.decision}`.toLowerCase().includes(query.toLowerCase()))
      ),
    [demoRequests, tenant, query]
  );
  const demoPageRows: Row[] = filteredDemo
    .slice(page * 10, page * 10 + 10)
    .map((r) => ({ requestId: r.requestId, tenant: r.tenant, decision: r.decision, latency: r.latency, time: r.time }));

  const isLive = mode === "live";
  const summary = isLive && liveSummary ? liveSummary : demoSummary;
  const rows: Row[] = isLive ? liveRows ?? [] : demoPageRows;
  const totalDecision = Object.values(summary.counts).reduce((a, b) => a + b, 0);
  const rangeEnd = isLive ? page * 10 + rows.length : Math.min((page + 1) * 10, filteredDemo.length);
  const hasNextPage = isLive ? rows.length === 10 : (page + 1) * 10 < filteredDemo.length;

  function selectTenant(v: string) {
    setTenant(v);
    setPage(0);
    setSelectedRow(null);
    setSelectedMock(null);
    setSelectedDetail(null);
    setRiskSavedNote(null);
  }

  function openRequest(row: Row) {
    setSelectedRow(row);
    setExpandedTools(false);
    if (isLive) {
      setSelectedDetail(null);
      consoleApi.eventDetail(row.requestId).then(setSelectedDetail).catch(() => setSelectedDetail(null));
    } else {
      setSelectedMock(demoRequests.find((r) => r.requestId === row.requestId) ?? null);
    }
  }

  function closeDrawer() {
    setSelectedRow(null);
    setSelectedMock(null);
    setSelectedDetail(null);
  }

  async function saveRisk(next: number) {
    setRisk(next);
    if (!isLive || !tenant) return;
    setRiskSaving(true);
    try {
      await consoleApi.setRiskAppetite(tenant, next, "showcase-console");
      setRiskSavedNote(`Saved · ${new Date().toLocaleTimeString()}`);
    } catch {
      setRiskSavedNote("Save failed — backend unreachable");
    } finally {
      setRiskSaving(false);
    }
  }

  async function review(agree: boolean) {
    if (isLive && selectedDetail) {
      try {
        await consoleApi.submitReview({
          request_id: selectedDetail.request.request_id,
          reviewer: "showcase-console",
          agree,
        });
        setReviewed((x) => ({ ...x, [selectedDetail.request.request_id]: agree }));
        const t = selectedDetail.request.tenant_id;
        consoleApi.humanAgreement(t).then((r) => setAgreement({ count: r.reviewed_count, rate: r.agreement_rate }));
        consoleApi.recalibration(t).then((r) => setRecalibration(r.suggestion));
        consoleApi.listReviews(t).then(setLiveReviews);
      } catch {
        // Backend write failed (e.g. connection dropped mid-session) — leave
        // the drawer state alone rather than claiming a review that wasn't
        // actually persisted to the audit ledger.
      }
      return;
    }
    if (selectedMock) setReviewed((x) => ({ ...x, [selectedMock.requestId]: agree }));
  }

  return (
    <div className="cp-console-shell">
      <header className="cp-console-topbar">
        <div className="cp-brand">
          <a href="/" className="cp-back">
            <ArrowLeft size={15} /> Showcase
          </a>
          <div className="cp-brand-mark">CP</div>
          <div>
            <div className="cp-brand-title">
              ControlPlane.ai <span>Governance Console</span>
            </div>
            <div className="cp-brand-sub">Live audit ledger · policy calibration · request inspection</div>
          </div>
        </div>
        <div className="cp-top-actions">
          <div className={`cp-live ${isLive ? "" : "cp-status-demo"}`} style={!isLive ? { color: "#e0b25c", background: "#1c1608", borderColor: "#43350f" } : undefined}>
            <span style={!isLive ? { background: "#e0b25c" } : undefined} /> {isLive ? "Audit ledger connected" : mode === "checking" ? "Connecting…" : "Demo data"}
          </div>
          <select value={tenant} onChange={(e) => selectTenant(e.target.value)}>
            <option value="">All tenants</option>
            {tenants.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <a href="https://github.com/MohithChandra07/Control-Plane-AIC" target="_blank" rel="noreferrer" className="cp-icon-btn" aria-label="GitHub">
            <Github size={16} />
          </a>
        </div>
      </header>

      <main className="cp-main">
        <div className="cp-page-head">
          <div>
            <div className="cp-kicker">Operational control plane</div>
            <h1>Governance overview</h1>
            <p>Monitor decisions, tune tenant scrutiny, and inspect the evidence behind every response.</p>
          </div>
          <div className="cp-live-meta">
            <span className="cp-live-dot" /> {isLive ? "LIVE" : "DEMO"} · updated{" "}
            {lastUpdate ? lastUpdate.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "—"}
          </div>
        </div>

        <div className={`cp-status-banner ${isLive ? "cp-status-live" : "cp-status-demo"}`}>
          {isLive ? <Wifi size={13} /> : <WifiOff size={13} />}
          <span className="cp-status-dot" />
          <span>
            {isLive
              ? "Connected to console/backend (via /api) — every number below is a live query against the audit ledger."
              : mode === "checking"
                ? "Checking for a running console/backend via the /api proxy…"
                : "No console/backend reachable via the /api proxy — showing deterministic showcase data instead."}
            {!isLive && probeError && (
              <>
                {" "}
                <span style={{ opacity: 0.75 }}>({probeError})</span>
              </>
            )}
          </span>
          {!isLive && mode !== "checking" && (
            <button
              type="button"
              onClick={retryProbe}
              className="cp-icon-btn"
              style={{ marginLeft: "auto", width: "auto", padding: "4px 10px", fontSize: 10 }}
              title="Retry connecting to console/backend"
            >
              <RefreshCw size={12} /> Retry
            </button>
          )}
        </div>

        <nav className="cp-tabs">
          {(
            [
              ["overview", "Overview"],
              ["interactions", "Interactions"],
              ["policy", "Policy Engine"],
              ["scrutiny", "Adaptive Scrutiny"],
              ["review", "Human Review"],
            ] as [Tab, string][]
          ).map(([key, label]) => (
            <button key={key} type="button" className={`cp-tab ${tab === key ? "active" : ""}`} onClick={() => setTab(key)}>
              {label}
            </button>
          ))}
        </nav>

        {tab === "overview" && (
          <>
            <div className="cp-metrics">
              {[
                ["TOTAL REQUESTS", summary.total.toLocaleString(), "Audited interactions"],
                ["ESCALATION RATE", `${summary.escalation.toFixed(1)}%`, "Human verification"],
                ["P50 LATENCY", `${summary.p50.toFixed(1)} ms`, "Typical decision path"],
                ["P95 LATENCY", `${summary.p95.toFixed(1)} ms`, "Tail decision path"],
              ].map(([label, value, sub]) => (
                <div className="cp-metric" key={label}>
                  <div className="cp-label">{label}</div>
                  <div className="cp-value">{value}</div>
                  <div className="cp-sub">{sub}</div>
                </div>
              ))}
            </div>

            <div className="cp-policy-grid" style={{ marginBottom: 12 }}>
              <div className="cp-policy-card">
                <h3>Interactions</h3>
                <p className="cp-policy-sub">latency of the {rows.length} most recent requests shown</p>
                {rows.length ? (
                  <MiniLineChart values={[...rows].reverse().map((r) => r.latency)} color="#00c2ff" />
                ) : (
                  <p className="cp-empty">No interactions yet.</p>
                )}
                <button type="button" className="cp-secondary" style={{ marginTop: 8 }} onClick={() => setTab("interactions")}>
                  Open Interactions →
                </button>
              </div>

              <div className="cp-policy-card">
                <h3>Policy Engine</h3>
                <p className="cp-policy-sub">risk thresholds by tenant (0–1 scale)</p>
                <MiniBarChart
                  groups={policies.map((p) => ({
                    label: p.tenant_id.replace("_", " ").slice(0, 10),
                    bars: [
                      { value: p.risk_thresholds.tier1_trigger, color: "#579af0", caption: `tier1 ${p.risk_thresholds.tier1_trigger}` },
                      { value: p.risk_thresholds.tier2_trigger, color: "#8b5cf6", caption: `tier2 ${p.risk_thresholds.tier2_trigger}` },
                      { value: p.risk_thresholds.block_trigger, color: "#ed5666", caption: `block ${p.risk_thresholds.block_trigger}` },
                    ],
                  }))}
                />
                <div className="cp-chip-row">
                  <span style={{ color: "#579af0" }}>■ tier1</span>
                  <span style={{ color: "#8b5cf6" }}>■ tier2</span>
                  <span style={{ color: "#ed5666" }}>■ block</span>
                </div>
                <button type="button" className="cp-secondary" style={{ marginTop: 8 }} onClick={() => setTab("policy")}>
                  Open Policy Engine →
                </button>
              </div>

              <div className="cp-policy-card">
                <h3>Adaptive Scrutiny</h3>
                <p className="cp-policy-sub">measured p95 latency vs. hallucination recall — benchmark, not live</p>
                <MiniBarChart
                  groups={SCRUTINY_MODES.map((m) => ({
                    label: m.mode.replace("ALWAYS_", "").slice(0, 8),
                    bars: [
                      { value: m.p95 / Math.max(...SCRUTINY_MODES.map((x) => x.p95)), color: "#8b5cf6", caption: `p95 ${m.p95}ms` },
                      { value: m.hallucinationRecall ?? 0, color: "#10b981", caption: `recall ${((m.hallucinationRecall ?? 0) * 100).toFixed(0)}%` },
                    ],
                  }))}
                />
                <div className="cp-chip-row">
                  <span style={{ color: "#8b5cf6" }}>■ p95 (relative)</span>
                  <span style={{ color: "#10b981" }}>■ hallucination recall</span>
                </div>
                <button type="button" className="cp-secondary" style={{ marginTop: 8 }} onClick={() => setTab("scrutiny")}>
                  Open Adaptive Scrutiny →
                </button>
              </div>
            </div>

            <Panel title={`Risk appetite — ${tenant || "all tenants"}`} right={<div className="cp-policy-chip"><ShieldCheck size={13} /> {isLive ? "live policy control" : "baseline policy"}</div>}>
              <div className="cp-risk-copy">
                <div>
                  <strong>Tenant scrutiny threshold</strong>
                  <p>
                    {isLive
                      ? "Select a single tenant above to read and adjust its live risk appetite via PUT /api/risk-appetite."
                      : "Adjust how aggressively Tier 0 routes traffic into Tier 1 verification. This is a policy control, not a cosmetic setting."}
                  </p>
                </div>
                <div className="cp-risk-value">
                  {risk.toFixed(2)} · {risk < 0.35 ? "Permissive" : risk > 0.65 ? "Strict" : "Balanced"}
                </div>
              </div>
              <div className="cp-slider-row">
                <span>Permissive</span>
                <input
                  aria-label="Risk appetite"
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={risk}
                  disabled={isLive && !tenant}
                  onChange={(e) => saveRisk(Number(e.target.value))}
                />
                <span>Strict</span>
              </div>
              <div className="cp-scale">
                <span>Lower scrutiny</span>
                <span>{isLive && tenant ? (riskSaving ? "Saving…" : riskSavedNote ?? "Configured baseline · " + tenant) : `Configured baseline · ${tenant || "tenant policy"}`}</span>
                <span>Higher scrutiny</span>
              </div>
            </Panel>

            <div className="cp-two-col">
              <Panel title="Human review" right={<Users size={15} />}>
                <div className="cp-review-stat">
                  <div>
                    <strong>{isLive ? agreement.count : Object.keys(reviewed).length + (tenant ? 1 : 0)}</strong>
                    <span>reviewed decisions</span>
                  </div>
                  <div>
                    <strong>{isLive ? (agreement.rate !== null ? `${(agreement.rate * 100).toFixed(0)}%` : "—") : `${Object.keys(reviewed).length ? Math.max(0, 100 - Object.values(reviewed).filter((v) => !v).length * 50) : 0}%`}</strong>
                    <span>agreement rate</span>
                  </div>
                </div>
                <div className="cp-review-row">
                  <span>Reviewer queue</span>
                  <span className="cp-muted">
                    {isLive
                      ? recalibration
                        ? recalibration.message
                        : "Agree/disagree decisions are persisted to the audit ledger."
                      : "Agree / disagree decisions are persisted to the audit path."}
                  </span>
                </div>
              </Panel>
              <Panel title="Decision distribution">
                <div className="cp-bars">
                  {(Object.entries(summary.counts) as [Decision, number][]).map(([d, c]) => (
                    <div className="cp-bar-row" key={d}>
                      <span>{d}</span>
                      <div className="cp-track">
                        <div className={`cp-bar ${decisionMeta[d].className}`} style={{ width: `${(c / Math.max(totalDecision, 1)) * 100}%` }} />
                      </div>
                      <strong>{c.toLocaleString()}</strong>
                    </div>
                  ))}
                </div>
              </Panel>
            </div>

            <div className="cp-footer">
              <span>ControlPlane.ai · AI Governance & Safety Gateway</span>
              <span>
                <Database size={12} /> {isLive ? "append-only audit ledger · live query" : "append-only audit surface · demo stream for showcase"}
              </span>
            </div>
          </>
        )}

        {tab === "interactions" && (
          <Panel
            title="Interactions · audit trail"
            right={
              <div className="cp-table-tools">
                {isLive ? (
                  <select value={decisionFilter} onChange={(e) => { setDecisionFilter(e.target.value); setPage(0); }}>
                    <option value="">All decisions</option>
                    {DECISIONS.map((d) => (
                      <option key={d} value={d}>
                        {d}
                      </option>
                    ))}
                  </select>
                ) : (
                  <div className="cp-search">
                    <Search size={14} />
                    <input
                      value={query}
                      onChange={(e) => {
                        setQuery(e.target.value);
                        setPage(0);
                      }}
                      placeholder="Search request, tenant, decision"
                    />
                  </div>
                )}
                <button className="cp-icon-btn" onClick={() => setLastUpdate(new Date())} title="Refresh">
                  <RefreshCw size={14} />
                </button>
              </div>
            }
          >
            <div className="cp-table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>TIME</th>
                    <th>TENANT</th>
                    <th>DECISION</th>
                    <th>LATENCY</th>
                    <th>REQUEST ID</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.requestId} onClick={() => openRequest(r)} className={selectedRow?.requestId === r.requestId ? "selected" : ""}>
                      <td>{r.time}</td>
                      <td>{r.tenant}</td>
                      <td>
                        <Badge decision={r.decision} />
                      </td>
                      <td>{r.latency.toFixed(1)} ms</td>
                      <td className="cp-id">{r.requestId.slice(0, 14)}…</td>
                    </tr>
                  ))}
                  {rows.length === 0 && (
                    <tr>
                      <td colSpan={5} className="cp-empty">
                        {isLive ? "No interactions in the ledger for this filter yet — run demo.replayer to populate it." : "No matching interactions."}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className="cp-pager">
              <span>
                {rows.length ? page * 10 + 1 : 0}–{rangeEnd}
                {isLive ? "" : ` of ${filteredDemo.length}`}
              </span>
              <div>
                <button disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))}>
                  Previous
                </button>
                <button disabled={!hasNextPage} onClick={() => setPage((p) => p + 1)}>
                  Next
                </button>
              </div>
            </div>
          </Panel>
        )}

        {tab === "policy" && (
          <div className="cp-policy-grid">
            {policies.map((p) => (
              <div className="cp-policy-card" key={p.tenant_id}>
                <h3>{p.display_name}</h3>
                <p className="cp-policy-sub">{p.tenant_id}.yaml</p>
                <p className="cp-desc">{p.description}</p>
                <div className="cp-kv-grid">
                  <div>
                    <span>Unverifiable handling</span>
                    <strong>{p.unverifiable_handling}</strong>
                  </div>
                  <div>
                    <span>Fail mode</span>
                    <strong>{p.fail_mode}</strong>
                  </div>
                  <div>
                    <span>Tier 1 trigger</span>
                    <strong>{p.risk_thresholds.tier1_trigger}</strong>
                  </div>
                  <div>
                    <span>Block trigger</span>
                    <strong>{p.risk_thresholds.block_trigger}</strong>
                  </div>
                  <div>
                    <span>Latency budget</span>
                    <strong>{p.latency_budget_ms} ms</strong>
                  </div>
                  <div>
                    <span>Max escalation rate</span>
                    <strong>{(p.escalation.max_escalation_rate * 100).toFixed(0)}%</strong>
                  </div>
                </div>
                <p className="cp-detail-title" style={{ marginTop: 12 }}>
                  PII hard-block categories
                </p>
                <div className="cp-chip-row">
                  {p.pii.hard_block_categories.length ? p.pii.hard_block_categories.map((c) => <span key={c}>{c}</span>) : <span>none</span>}
                </div>
                <p className="cp-detail-title" style={{ marginTop: 12 }}>
                  Consequential tool sinks {p.tool_calls.enabled ? "" : "(disabled for this tenant)"}
                </p>
                <div className="cp-chip-row">
                  {p.tool_calls.consequential_sinks.length ? (
                    p.tool_calls.consequential_sinks.map((s) => <span key={s}>{s}</span>)
                  ) : (
                    <span>none</span>
                  )}
                </div>
                <p className="cp-drawer-note" style={{ marginTop: 14 }}>
                  <ScrollText size={12} /> Tainted argument to a gated sink → {p.tool_calls.tainted_argument_action}
                </p>
              </div>
            ))}
          </div>
        )}

        {tab === "scrutiny" && (
          <>
            <Panel title="Scrutiny configurations" right={<span className="cp-policy-chip"><Timer size={13} /> measured</span>}>
              <div style={{ padding: "16px" }}>
                {SCRUTINY_MODES.map((m) => (
                  <div key={m.mode} className={`cp-scrutiny-card ${m.mode === "ADAPTIVE" ? "adaptive" : ""}`}>
                    <div className="cp-scrutiny-head">
                      <strong>{m.mode}</strong>
                      <span>
                        p50 {m.p50.toFixed(2)}ms · p95 {m.p95.toFixed(2)}ms
                      </span>
                    </div>
                    <p style={{ margin: "6px 0 0", fontSize: 12, color: "#9aa8bd" }}>{m.blurb}</p>
                    <div className="cp-bar-row" style={{ marginTop: 10 }}>
                      <span>RECALL</span>
                      <div className="cp-track">
                        <div className="cp-bar cp-allow" style={{ width: `${Math.max((m.hallucinationRecall ?? 0) * 100, 1.5)}%` }} />
                      </div>
                      <strong>{m.hallucinationRecall === null ? "—" : `${(m.hallucinationRecall * 100).toFixed(1)}%`}</strong>
                    </div>
                  </div>
                ))}
                <p className="cp-drawer-note">
                  <Layers size={12} /> {BENCH_SOURCE}
                </p>
              </div>
            </Panel>
            <Panel title="Risk appetite sweep" right={<span className="cp-policy-chip"><SlidersHorizontal size={13} /> benchmark</span>}>
              <div className="cp-table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>APPETITE</th>
                      <th>TIER 1 RATE</th>
                      <th>ESCALATION</th>
                      <th>P95</th>
                      <th>HALLU. RECALL</th>
                    </tr>
                  </thead>
                  <tbody>
                    {APPETITE_SWEEP.map((p) => (
                      <tr key={p.appetite}>
                        <td>{p.appetite.toFixed(2)}</td>
                        <td>{(p.tier1Rate * 100).toFixed(1)}%</td>
                        <td>{(p.escalationRate * 100).toFixed(1)}%</td>
                        <td>{p.p95.toFixed(2)} ms</td>
                        <td>{(p.hallucinationRecall * 100).toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="cp-drawer-note">
                <Layers size={12} /> {APPETITE_SOURCE}
              </p>
            </Panel>
          </>
        )}

        {tab === "review" && (
          <Panel title="Human review queue" right={<Users size={15} />}>
            <div className="cp-review-stat">
              <div>
                <strong>{isLive ? agreement.count : Object.keys(reviewed).length}</strong>
                <span>reviewed decisions</span>
              </div>
              <div>
                <strong>{isLive ? (agreement.rate !== null ? `${(agreement.rate * 100).toFixed(0)}%` : "—") : "—"}</strong>
                <span>agreement rate</span>
              </div>
            </div>
            {isLive && recalibration && (
              <div className="cp-review-row">
                <span>Recalibration suggestion</span>
                <span className="cp-muted">{recalibration.message}</span>
              </div>
            )}
            <div className="cp-table-wrap">
              {isLive ? (
                <table>
                  <thead>
                    <tr>
                      <th>WHEN</th>
                      <th>REQUEST</th>
                      <th>REVIEWER</th>
                      <th>VERDICT</th>
                    </tr>
                  </thead>
                  <tbody>
                    {liveReviews.map((r, i) => (
                      <tr key={i}>
                        <td>{new Date(r.created_at).toLocaleString()}</td>
                        <td className="cp-id">{(r.reviewed_request_id ?? "").slice(0, 14)}…</td>
                        <td>{r.reviewer ?? "—"}</td>
                        <td>{r.agree ? "Agree" : "Disagree"}</td>
                      </tr>
                    ))}
                    {liveReviews.length === 0 && (
                      <tr>
                        <td colSpan={4} className="cp-empty">
                          No reviews recorded yet — open an interaction and click Agree/Disagree.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              ) : (
                <p className="cp-empty">Open an interaction from the Interactions tab and record Agree/Disagree — reviews are demo-local until a backend is connected.</p>
              )}
            </div>
          </Panel>
        )}
      </main>

      {(selectedMock || selectedDetail || (selectedRow && isLive)) && (
        <div className="cp-drawer-overlay" onClick={closeDrawer}>
          <aside className="cp-drawer" onClick={(e) => e.stopPropagation()}>
            <div className="cp-drawer-head">
              <div>
                <div className="cp-kicker">Request inspection</div>
                <h2>{selectedRow?.requestId}</h2>
                <p>
                  {selectedRow?.tenant} · <Badge decision={selectedRow?.decision ?? ""} />
                </p>
              </div>
              <button className="cp-icon-btn" onClick={closeDrawer} aria-label="Close">
                <X size={16} />
              </button>
            </div>

            {isLive ? (
              selectedDetail ? (
                <>
                  <div className="cp-detail-section">
                    <div className="cp-detail-title">Request metadata</div>
                    <div className="cp-meta-grid">
                      <div>
                        <span>conversation_id</span>
                        <strong>{selectedDetail.request.conversation_id ?? "—"}</strong>
                      </div>
                      <div>
                        <span>turn_id</span>
                        <strong>{selectedDetail.request.turn_id ?? "—"}</strong>
                      </div>
                      <div>
                        <span>latency</span>
                        <strong>{selectedDetail.request.latency_ms?.toFixed(1) ?? "—"} ms</strong>
                      </div>
                      <div>
                        <span>model_used</span>
                        <strong>{(selectedDetail.request.action?.model_used as string) ?? "not tracked"}</strong>
                      </div>
                    </div>
                  </div>
                  <div className="cp-detail-section">
                    <div className="cp-detail-title">Claims ({selectedDetail.claims.length})</div>
                    {selectedDetail.claims.length === 0 ? (
                      <div className="cp-empty">No claims extracted (Tier 0 only).</div>
                    ) : (
                      selectedDetail.claims.map((c) => (
                        <div className="cp-claim" key={c.claim_id}>
                          <div className="cp-claim-head">
                            <Badge decision={c.remediation ?? "ALLOW"} />
                            <span className="cp-verdict">{c.verdict}</span>
                            {c.taint_status === "tainted" && <span className="cp-taint">TAINTED</span>}
                          </div>
                          <p>{c.claim_text}</p>
                          <div className="cp-tags">
                            {c.risk_labels &&
                              Object.entries(c.risk_labels)
                                .filter(([, v]) => v.evaluated && v.detected)
                                .map(([label]) => <span key={label}>{label}</span>)}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                  <div className="cp-detail-section">
                    <button className="cp-expand" onClick={() => setExpandedTools((x) => !x)}>
                      <span>
                        {expandedTools ? <ChevronDown size={14} /> : <ChevronRight size={14} />} Tool calls ({selectedDetail.tool_calls.length})
                      </span>
                      <span className="cp-muted">provenance & taint</span>
                    </button>
                    {expandedTools &&
                      (selectedDetail.tool_calls.length ? (
                        selectedDetail.tool_calls.map((t, i) => (
                          <div className="cp-tool" key={i}>
                            <div>
                              <strong>{(t.action?.tool_name as string) ?? "tool_call"}</strong>
                              <Badge decision={t.remediation ?? "ALLOW"} />
                            </div>
                            <pre>{JSON.stringify(t.action, null, 2)}</pre>
                          </div>
                        ))
                      ) : (
                        <div className="cp-empty">No tool calls in this response.</div>
                      ))}
                  </div>
                  <div className="cp-detail-section">
                    <div className="cp-detail-title">Reviewer verdict</div>
                    <div className="cp-review-actions">
                      <button className="cp-secondary" onClick={() => review(true)}>
                        Agree
                      </button>
                      <button className="cp-secondary" onClick={() => review(false)}>
                        Disagree
                      </button>
                      {reviewed[selectedDetail.request.request_id] !== undefined && (
                        <span className="cp-reviewed">Recorded · {reviewed[selectedDetail.request.request_id] ? "agree" : "disagree"}</span>
                      )}
                    </div>
                  </div>
                  <div className="cp-drawer-note">
                    <ShieldCheck size={14} /> Live inspection: every field above is a query against the hash-chained audit ledger.
                  </div>
                </>
              ) : (
                <div className="cp-empty">Loading…</div>
              )
            ) : selectedMock ? (
              <>
                <div className="cp-detail-section">
                  <div className="cp-detail-title">Request metadata</div>
                  <div className="cp-meta-grid">
                    {Object.entries(selectedMock.metadata).map(([k, v]) => (
                      <div key={k}>
                        <span>{k}</span>
                        <strong>{v}</strong>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="cp-detail-section">
                  <div className="cp-detail-title">Claims ({selectedMock.claims.length})</div>
                  {selectedMock.claims.length === 0 ? (
                    <div className="cp-empty">No claims extracted (Tier 0 only).</div>
                  ) : (
                    selectedMock.claims.map((c) => (
                      <div className="cp-claim" key={c.id}>
                        <div className="cp-claim-head">
                          <Badge decision={c.remediation} />
                          <span className="cp-verdict">{c.verdict}</span>
                          {c.taint === "tainted" && <span className="cp-taint">TAINTED</span>}
                        </div>
                        <p>{c.text}</p>
                        <div className="cp-tags">
                          {c.risk.map((r) => (
                            <span key={r}>{r}</span>
                          ))}
                        </div>
                      </div>
                    ))
                  )}
                </div>
                <div className="cp-detail-section">
                  <button className="cp-expand" onClick={() => setExpandedTools((x) => !x)}>
                    <span>
                      {expandedTools ? <ChevronDown size={14} /> : <ChevronRight size={14} />} Tool calls ({selectedMock.tools.length})
                    </span>
                    <span className="cp-muted">provenance & taint</span>
                  </button>
                  {expandedTools &&
                    (selectedMock.tools.length ? (
                      selectedMock.tools.map((t, i) => (
                        <div className="cp-tool" key={i}>
                          <div>
                            <strong>{t.name}</strong>
                            <Badge decision={t.remediation} />
                          </div>
                          <pre>{t.action}</pre>
                          <div className="cp-tool-meta">
                            <span>source: {t.provenance}</span>
                            <span>taint: {t.taint}</span>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="cp-empty">No tool calls in this response.</div>
                    ))}
                </div>
                <div className="cp-detail-section">
                  <div className="cp-detail-title">Reviewer verdict</div>
                  <div className="cp-review-actions">
                    <button className="cp-secondary" onClick={() => review(true)}>
                      Agree
                    </button>
                    <button className="cp-secondary" onClick={() => review(false)}>
                      Disagree
                    </button>
                    {reviewed[selectedMock.requestId] !== undefined && (
                      <span className="cp-reviewed">Recorded · {reviewed[selectedMock.requestId] ? "agree" : "disagree"}</span>
                    )}
                  </div>
                </div>
                <div className="cp-drawer-note">
                  <CircleHelp size={14} /> Inspection data is deterministic showcase data; connect console/backend on :8001 for live ledger data.
                </div>
              </>
            ) : null}
          </aside>
        </div>
      )}
    </div>
  );
}
