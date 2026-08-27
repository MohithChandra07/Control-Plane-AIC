# Project Brief

## What ControlPlane is

ControlPlane is an AI governance and safety gateway. It sits between an
application and an AI model/agent — an OpenAI-compatible drop-in, so
adopting it is meant to be "change the base URL," not "rewrite the
application." It inspects what goes in (retrieved documents, tool
results) and what comes out (claims, PII, tool calls), and lets **policy**
— not silent model behavior — decide whether a response or a tool call is
allowed, modified, escalated, or blocked.

## Why it exists

LLM applications routinely let three failure modes reach users or
real-world systems unchecked:

1. **Hallucinated or unverifiable claims presented as fact** ("your
   refund is ₹48,000") with no distinction between "confirmed true,"
   "confirmed false," and "we don't actually know."
2. **PII leaking into responses** because nothing downstream is looking
   for it.
3. **Consequential actions triggered from unverified information** — an
   agent calling `issue_refund(amount=48000)` because the amount
   "sounded right" in an earlier turn, with no trace back to whether that
   number was ever actually confirmed.

Most systems attempting to address this collapse into "proxy + regex PII
filter + LLM judge + block button." ControlPlane's bet is that the useful
version of this is more surgical: claim-level (not response-level)
remediation, explicit three-way verification verdicts, provenance and
taint that survive across conversation turns and into tool-call
arguments, and policy that's configuration, not code.

## Who it's for

Three illustrative tenant profiles drive the policy differentiation
(`configs/*.yaml`):

- **Customer support assistant** — customer-facing, conservative, tight
  latency budget (150ms), redacts PII, hedges what it can't confirm.
- **Internal knowledge copilot** — internal-only, more tolerant of
  unverifiable information since the audience can cross-check it
  themselves, looser latency budget (600ms).
- **Regulated decision-support agent** — has consequential tool access
  (e.g. issuing refunds), strictest verification requirements, tool-call
  gating enabled, latency budget 2s.

## Current state

Phases 1–5 (Foundation, Basic Governance, Agent Safety, Observability +
Evaluation, Calibration + Demo Hardening) are implemented — see
`docs/roadmap.md` for what's actually done versus what's a documented
simplification, and `README.md` for how to run it. Nothing in this
repository claims more than what's been built and tested.
