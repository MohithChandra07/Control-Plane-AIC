/**
 * Interactive Gateway demo (spec §7).
 *
 * These four walkthroughs are precomputed, not a live model call — there is
 * no upstream provider key in a static showcase deploy. Every outcome below
 * is read straight off the real tenant policy it names (configs/*.yaml via
 * policy/models.py), not invented for effect: the citation on each stage is
 * the actual YAML field driving that stage's outcome. Scene 2 reproduces the
 * exact trace in components/sections/TaintEngine.tsx and
 * tests/integration/test_gateway_scenes_5_7.py.
 *
 * This is a demonstration of the policy shape, not a duplicate of the
 * governance engine — policy/engine.py remains the only place a real
 * decision is made. Wiring this to a live request is a POST to
 * `${NEXT_PUBLIC_GATEWAY_URL}/v1/chat/completions` with an
 * `X-ControlPlane-Tenant` header set to the scenario's tenantId; see
 * gateway/routes/chat.py.
 */

export type StageStatus = "pass" | "flag" | "block";

export interface PipelineStage {
  key: "performance" | "cost" | "responsibility" | "scrutiny" | "policy";
  label: string;
  status: StageStatus;
  readout: string;
  citation: string;
}

export type DemoDecision = "ALLOW" | "MODIFY" | "ESCALATE" | "BLOCK";

export interface GatewayScenario {
  id: string;
  tenantId: "customer_support" | "internal_copilot" | "regulated_agent";
  tenantLabel: string;
  configFile: string;
  prompt: string;
  responseExcerpt: string;
  stages: PipelineStage[];
  decision: DemoDecision;
  decisionNote: string;
}

const DECISION_META: Record<DemoDecision, { note: string }> = {
  ALLOW: { note: "Untouched. Nothing to remediate." },
  MODIFY: { note: "Surgical: hedge, redact, cite, or remove — never the whole response." },
  ESCALATE: { note: "Routed to a human reviewer before it ships." },
  BLOCK: { note: "Reserved: a hard-block PII category, or a gated tool call." },
};

export const GATEWAY_SCENARIOS: GatewayScenario[] = [
  {
    id: "refund-hedge",
    tenantId: "customer_support",
    tenantLabel: "Customer Support Assistant",
    configFile: "configs/customer_support.yaml",
    prompt: "Can you refund this customer's payment?",
    responseExcerpt:
      "“Refunds are available within 43 days of purchase, so this should qualify.”",
    stages: [
      {
        key: "performance",
        label: "Performance",
        status: "flag",
        readout: "Claim extracted — grounding check against corpus finds no support for ‘43 days’",
        citation: "detectors/hallucination/claim_verifier.py → verdict CONTRADICTED",
      },
      {
        key: "cost",
        label: "Cost",
        status: "pass",
        readout: "Within tenant token/latency budget",
        citation: "customer_support.yaml → latency_budget_ms: 150",
      },
      {
        key: "responsibility",
        label: "Responsibility",
        status: "flag",
        readout: "No PII, no injection — one hallucination risk label on this claim",
        citation: "detectors/responsibility → risk_labels: [hallucination]",
      },
      {
        key: "scrutiny",
        label: "Adaptive Scrutiny",
        status: "flag",
        readout: "Score above tier1_trigger — escalated to full Tier 1 verification",
        citation: "customer_support.yaml → risk_thresholds.tier1_trigger: 0.3",
      },
      {
        key: "policy",
        label: "Policy Engine",
        status: "flag",
        readout: "CONTRADICTED claim → surgical hedge remediation, not a full block",
        citation: "customer_support.yaml → unverifiable_handling: HEDGE",
      },
    ],
    decision: "MODIFY",
    decisionNote: DECISION_META.MODIFY.note,
  },
  {
    id: "refund-taint-block",
    tenantId: "regulated_agent",
    tenantLabel: "Regulated Decision-Support Agent",
    configFile: "configs/regulated_agent.yaml",
    prompt: "Issue a ₹48,000 refund based on the amount the customer says they're owed.",
    responseExcerpt: 'issue_refund({ "amount": 48000, "currency": "INR" })',
    stages: [
      {
        key: "performance",
        label: "Performance",
        status: "flag",
        readout: "₹48,000 traced to an earlier UNVERIFIABLE claim, not a verified source",
        citation: "ledger/taint.py → provenance lookup against the audit ledger",
      },
      {
        key: "cost",
        label: "Cost",
        status: "pass",
        readout: "Single call, no retry storm — breaker not tripped",
        citation: "regulated_agent.yaml → cost_breaker.max_requests_per_window: 20",
      },
      {
        key: "responsibility",
        label: "Responsibility",
        status: "block",
        readout: "issue_refund is a money_movement sink — tainted argument reaches it",
        citation: "data/tools.yaml → issue_refund.sink: money_movement",
      },
      {
        key: "scrutiny",
        label: "Adaptive Scrutiny",
        status: "flag",
        readout: "Consequential tool call — always resolved against the ledger, tier bypassed",
        citation: "regulated_agent.yaml → tool_calls.enabled: true",
      },
      {
        key: "policy",
        label: "Policy Engine",
        status: "block",
        readout: "Tainted argument to a consequential sink → hard block, tool call stripped",
        citation: "regulated_agent.yaml → tool_calls.tainted_argument_action: BLOCK",
      },
    ],
    decision: "BLOCK",
    decisionNote: DECISION_META.BLOCK.note,
  },
  {
    id: "card-number-block",
    tenantId: "customer_support",
    tenantLabel: "Customer Support Assistant",
    configFile: "configs/customer_support.yaml",
    prompt: "Here's my card number 4111 1111 1111 1111 — can you update my file with it?",
    responseExcerpt: "“I've noted card ending 1111 against your account.”",
    stages: [
      {
        key: "performance",
        label: "Performance",
        status: "pass",
        readout: "No unverifiable claim in the response itself",
        citation: "detectors/hallucination → no claims flagged",
      },
      {
        key: "cost",
        label: "Cost",
        status: "pass",
        readout: "Within tenant token/latency budget",
        citation: "customer_support.yaml → latency_budget_ms: 150",
      },
      {
        key: "responsibility",
        label: "Responsibility",
        status: "block",
        readout: "Credit-card number detected in the user turn",
        citation: "detectors/pii → category: credit_card",
      },
      {
        key: "scrutiny",
        label: "Adaptive Scrutiny",
        status: "flag",
        readout: "PII hit — always promoted to full Tier 1 handling",
        citation: "customer_support.yaml → pii.enabled: true",
      },
      {
        key: "policy",
        label: "Policy Engine",
        status: "block",
        readout: "credit_card is a hard-block category for this tenant, default REDACT overridden",
        citation: "customer_support.yaml → pii.hard_block_categories: [credit_card, government_id]",
      },
    ],
    decision: "BLOCK",
    decisionNote: DECISION_META.BLOCK.note,
  },
  {
    id: "internal-pto-allow",
    tenantId: "internal_copilot",
    tenantLabel: "Internal Knowledge Copilot",
    configFile: "configs/internal_copilot.yaml",
    prompt: "What's our internal PTO policy for new hires?",
    responseExcerpt:
      "“New hires typically accrue PTO from day one, though check with HR for your specific offer.”",
    stages: [
      {
        key: "performance",
        label: "Performance",
        status: "flag",
        readout: "Claim not found in the corpus — UNVERIFIABLE, not treated as false",
        citation: "docs/terminology.md → UNVERIFIABLE ≠ FALSE",
      },
      {
        key: "cost",
        label: "Cost",
        status: "pass",
        readout: "Cheap-model-first routing handled this turn, no escalation needed",
        citation: "internal_copilot.yaml → model_routing.cheap_model: gpt-4o-mini",
      },
      {
        key: "responsibility",
        label: "Responsibility",
        status: "pass",
        readout: "No PII, no injection, no policy risk labels",
        citation: "internal_copilot.yaml → pii.enabled: true (nothing matched)",
      },
      {
        key: "scrutiny",
        label: "Adaptive Scrutiny",
        status: "pass",
        readout: "Score under tier1_trigger for this tenant — Tier 0 gate is sufficient",
        citation: "internal_copilot.yaml → risk_thresholds.tier1_trigger: 0.5",
      },
      {
        key: "policy",
        label: "Policy Engine",
        status: "pass",
        readout: "Internal audience can self-verify — unverifiable claims allowed through",
        citation: "internal_copilot.yaml → unverifiable_handling: ALLOW",
      },
    ],
    decision: "ALLOW",
    decisionNote: DECISION_META.ALLOW.note,
  },
];
