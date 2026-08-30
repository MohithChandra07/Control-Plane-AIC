/**
 * Client for the real ControlPlane console backend (console/backend/main.py)
 * — the same read/write API console/frontend uses.
 *
 * Every request below is a *relative* same-origin path (e.g. "/api/tenants").
 * The browser never talks to the backend's host/port directly — Next's own
 * server rewrites `/api/*` to console/backend server-to-server (see
 * next.config.mjs's `rewrites()`, and CONSOLE_BACKEND_URL there). That's
 * deliberate: a server-to-server proxy call isn't subject to the browser's
 * CORS policy, so this can't fail as a cross-origin block no matter what
 * port the showcase or the backend run on — the previous cross-origin
 * `fetch("http://host:port/api/...")` approach could.
 *
 * The showcase console tries this first; every call has a short timeout, so
 * when the backend isn't running (the common case for a static showcase
 * deploy) callers fall back to the deterministic demo data in ./mockData
 * within ~3s rather than hanging. See components/console/ConsoleApp.tsx
 * for how the two are stitched together and clearly labeled.
 */

/**
 * Turns a fetch failure into a short, actionable reason rather than a bare
 * "TypeError: Failed to fetch" — this is what the console's status banner
 * shows, so a reader can tell "backend not running" apart from "backend
 * responded but errored" apart from "browser blocked it as cross-origin"
 * without opening devtools.
 */
function describeError(err: unknown, path: string): Error {
  if (err instanceof DOMException && err.name === "AbortError") {
    return new Error(`${path} timed out — the backend didn't answer in time`);
  }
  if (err instanceof TypeError) {
    // This is a same-origin request proxied by Next's own server (see
    // next.config.mjs), so it can't be a browser CORS block — a failure
    // here means the showcase's own dev/prod server isn't reachable at all
    // (wrong port, not running).
    return new Error(`${path} — could not reach the showcase server itself (is it running?)`);
  }
  return err instanceof Error ? err : new Error(String(err));
}

async function get<T>(path: string, timeoutMs = 3000): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(path, { signal: controller.signal });
    if (!response.ok) {
      const body = await response.text().catch(() => "");
      throw new Error(`${path} → HTTP ${response.status}${body ? ` — ${body.slice(0, 200)}` : ""}`);
    }
    return (await response.json()) as T;
  } catch (err) {
    throw describeError(err, path);
  } finally {
    clearTimeout(timer);
  }
}

async function send<T>(path: string, method: "POST" | "PUT", body: unknown, timeoutMs = 2500): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(path, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (!response.ok) {
      const body = await response.text().catch(() => "");
      throw new Error(`${path} → HTTP ${response.status}${body ? ` — ${body.slice(0, 200)}` : ""}`);
    }
    return (await response.json()) as T;
  } catch (err) {
    throw describeError(err, path);
  } finally {
    clearTimeout(timer);
  }
}

export interface RiskFinding {
  detected: boolean;
  score: number;
  evaluated: boolean;
}

export interface LiveClaim {
  claim_id: string;
  claim_text: string;
  verdict: "SUPPORTED" | "CONTRADICTED" | "UNVERIFIABLE";
  risk_labels: Record<"hallucination" | "pii" | "policy" | "toxicity" | "bias", RiskFinding> | null;
  provenance: { source: string; source_id?: string | null; verdict: string } | null;
  taint_status: string | null;
  remediation: string | null;
}

export interface LiveToolCall {
  remediation: string | null;
  action: Record<string, unknown> | null;
}

export interface LiveEvent {
  request_id: string;
  tenant_id: string;
  conversation_id: string | null;
  turn_id: number | null;
  decision: string;
  latency_ms: number | null;
  error: string | null;
  created_at: string;
}

export interface LiveEventDetail {
  request: LiveEvent & { action: Record<string, unknown> | null };
  claims: LiveClaim[];
  tool_calls: LiveToolCall[];
  reviews: { created_at: string; reviewer?: string; agree?: boolean; notes?: string | null }[];
}

export interface LiveSummary {
  total_requests: number;
  decision_counts: Record<string, number>;
  escalation_rate: number | null;
  latency_ms: { p50: number | null; p95: number | null };
}

export interface LivePolicy {
  tenant_id: string;
  display_name: string;
  description: string;
  latency_budget_ms: number;
  unverifiable_handling: string;
  risk_thresholds: { tier1_trigger: number; tier2_trigger: number; block_trigger: number };
  pii: { enabled: boolean; remediation: string; hard_block_categories: string[] };
  tool_calls: {
    enabled: boolean;
    consequential_sinks: string[];
    tainted_argument_action: string;
    require_verified_provenance: boolean;
  };
  escalation: { enabled: boolean; max_escalation_rate: number };
  cost_breaker: { enabled: boolean; window_seconds: number; max_requests_per_window: number; max_tokens_per_window: number };
  model_routing: { enabled: boolean; cheap_model: string; escalation_model: string };
  fail_mode: string;
}

export interface DemoRequestPayload {
  name: string;
  work_email: string;
  company: string;
  role: string;
  ai_use_case: string;
  primary_concern: string;
}

/**
 * Posts the "Request a demo" form. Deliberately not built on the generic
 * get()/send() helpers above: those are tuned for the console's internal
 * tooling, where a raw HTTP-status-plus-body error string is useful
 * diagnostic detail. Here the audience is a site visitor, so a failure is
 * translated into one clean, user-facing sentence — never Resend's or
 * FastAPI's raw error text (see console/backend/main.py's own comment on
 * the same boundary).
 */
export async function submitDemoRequest(payload: DemoRequestPayload): Promise<void> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10_000);
  let response: Response;
  try {
    response = await fetch("/api/demo-request", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
  } catch {
    throw new Error("Couldn't reach the server. Check your connection and try again.");
  } finally {
    clearTimeout(timer);
  }

  if (response.ok) return;

  // FastAPI's own detail is either a plain string (our handler's 502/503)
  // or a pydantic validation-error array (422) — only the plain-string
  // case is safe to show verbatim; the array case gets a generic message
  // rather than surfacing pydantic's internal field-path structure.
  let detail: string | undefined;
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") detail = body.detail;
  } catch {
    // Non-JSON error body — fall through to the generic message below.
  }

  if (response.status === 422) {
    throw new Error("Please check your details and try again.");
  }
  throw new Error(detail || "Something went wrong submitting your request. Please try again shortly.");
}

export const consoleApi = {
  tenants: () => get<string[]>("/api/tenants"),
  policies: () => get<LivePolicy[]>("/api/policies"),
  summary: (tenant?: string) => get<LiveSummary>(`/api/summary${tenant ? `?tenant=${tenant}` : ""}`),
  events: (params: { tenant?: string; decision?: string; limit?: number; offset?: number }) => {
    const q = new URLSearchParams();
    if (params.tenant) q.set("tenant", params.tenant);
    if (params.decision) q.set("decision", params.decision);
    q.set("limit", String(params.limit ?? 10));
    q.set("offset", String(params.offset ?? 0));
    return get<LiveEvent[]>(`/api/events?${q.toString()}`);
  },
  eventDetail: (requestId: string) => get<LiveEventDetail>(`/api/events/${requestId}`),
  riskAppetite: (tenant: string) =>
    get<{ tenant_id: string; risk_appetite: number; updated_at: string | null; updated_by: string | null }>(
      `/api/risk-appetite/${tenant}`
    ),
  setRiskAppetite: (tenant: string, risk_appetite: number, updated_by: string) =>
    send(`/api/risk-appetite/${tenant}`, "PUT", { risk_appetite, updated_by }),
  submitReview: (body: { request_id: string; claim_id?: string | null; reviewer: string; agree: boolean }) =>
    send<{ status: string }>("/api/reviews", "POST", body),
  listReviews: (tenant?: string) =>
    get<{ tenant_id: string; created_at: string; reviewed_request_id?: string; reviewer?: string; agree?: boolean }[]>(
      `/api/reviews${tenant ? `?tenant=${tenant}` : ""}`
    ),
  humanAgreement: (tenant: string) =>
    get<{ tenant_id: string; reviewed_count: number; agreement_rate: number | null }>(
      `/api/human-agreement/${tenant}`
    ),
  recalibration: (tenant: string) =>
    get<{
      tenant_id: string;
      suggestion: {
        reviewed_count: number;
        disagreement_rate: number;
        suggested_appetite_delta: number;
        message: string;
      } | null;
    }>(`/api/recalibration/${tenant}`),
};
