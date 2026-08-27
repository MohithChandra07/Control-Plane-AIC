export interface Summary {
  total_requests: number;
  decision_counts: Record<string, number>;
  escalation_rate: number | null;
  latency_ms: { p50: number | null; p95: number | null };
}

export interface EventRow {
  request_id: string;
  tenant_id: string;
  conversation_id: string | null;
  turn_id: number | null;
  decision: string;
  latency_ms: number | null;
  error: string | null;
  created_at: string;
}

export interface RiskFinding {
  detected: boolean;
  score: number;
  evaluated: boolean;
}

export interface Claim {
  claim_id: string | null;
  claim_text: string | null;
  verdict: string | null;
  risk_labels: Record<string, RiskFinding> | null;
  provenance: Record<string, unknown> | null;
  taint_status: string | null;
  remediation: string | null;
}

export interface ToolCallRow {
  remediation: string | null;
  action: Record<string, unknown> | null;
}

export interface EventDetail {
  request: EventRow & { action: Record<string, unknown> | null };
  claims: Claim[];
  tool_calls: ToolCallRow[];
}
