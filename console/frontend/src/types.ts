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

export interface Review {
  created_at: string;
  reviewed_request_id: string;
  reviewed_claim_id: string | null;
  reviewed_decision: string | null;
  reviewer: string;
  agree: boolean;
  notes: string | null;
}

export interface EventDetail {
  request: EventRow & { action: Record<string, unknown> | null };
  claims: Claim[];
  tool_calls: ToolCallRow[];
  reviews: Review[];
}

export interface HumanAgreement {
  tenant_id: string;
  reviewed_count: number;
  agreement_rate: number | null;
}

export interface RecalibrationSuggestion {
  reviewed_count: number;
  disagreement_rate: number;
  suggested_appetite_delta: number;
  message: string;
}

export interface Recalibration {
  tenant_id: string;
  suggestion: RecalibrationSuggestion | null;
}

export interface RiskAppetite {
  tenant_id: string;
  risk_appetite: number;
  updated_at: string | null;
  updated_by: string | null;
}
