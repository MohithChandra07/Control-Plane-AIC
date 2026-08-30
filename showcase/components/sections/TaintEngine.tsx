"use client";

import { Ban, FileWarning, GitBranch, ShieldAlert, Zap } from "lucide-react";

import { Section } from "./Section";
import { GlassCard, SectionLabel } from "@/components/ui/Glass";
import { Reveal } from "@/components/ui/Reveal";
import { cn } from "@/lib/utils";

/**
 * Section 03 — Scene 7, the one that matters most.
 *
 * Rendered as a three-step trace rather than prose because the point is the
 * *link* between turns: an unverifiable claim in turn 1 is what kills the tool
 * call in turn 2. Every string here matches the assertions in
 * tests/integration/test_gateway_scenes_5_7.py.
 */

interface Step {
  turn: string;
  title: string;
  payload: string;
  verdict: string;
  verdictColor: string;
  note: string;
}

const TRACE: Step[] = [
  {
    turn: "Turn 1",
    title: "Agent asserts an amount",
    payload: "Customer is owed ₹48,000 according to their message, though this is unconfirmed.",
    verdict: "UNVERIFIABLE",
    verdictColor: "#f59e0b",
    note: "No corpus backing. Not false — unconfirmable. The claim is recorded tainted, with its provenance, on the hash-chained ledger.",
  },
  {
    turn: "Turn 2",
    title: "Agent proposes an action",
    payload: 'issue_refund({ "amount": 48000, "currency": "INR" })',
    verdict: "CONSEQUENTIAL SINK",
    verdictColor: "#3b82f6",
    note: "The tool catalog marks issue_refund consequential, so its arguments are resolved against the ledger for this conversation — matching across ₹-formatting.",
  },
  {
    turn: "Gate",
    title: "Tool call never ships",
    payload: "tool_calls stripped from the response · decision = BLOCK",
    verdict: "BLOCK",
    verdictColor: "#ef4444",
    note: "The application never receives a green-lit call to execute. The same tool with an untainted amount passes as ALLOW — this is taint, not a blanket deny.",
  },
];

const DEFENCES = [
  {
    icon: ShieldAlert,
    accent: "#f59e0b",
    title: "Prompt Injection Shield",
    body: 'Only role="tool" and role="function" messages are scanned — the convention for retrieved content. The matched span alone is replaced with [REDACTED_INJECTION_ATTEMPT]; the surrounding document survives, and the model never sees the instruction.',
    proof: "tests/integration/test_scene4_injection.py asserts against the exact payload the provider received",
  },
  {
    icon: Zap,
    accent: "#10b981",
    title: "Cost Circuit Breaker",
    body: "A per-tenant sliding window over request count and token volume, checked before the upstream call. When it trips: 429 returned, zero provider cost incurred, and the trip audited with its reason rather than swallowed.",
    proof: "31 rapid requests → provider called exactly 30 times",
  },
];

export function TaintEngine() {
  return (
    <Section id="taint" index={2}>
      <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:gap-14">
        <div className="pointer-events-auto">
          <Reveal>
            <SectionLabel index="03">Taint Engine</SectionLabel>
          </Reveal>

          <Reveal delay={0.08}>
            <h2 className="mt-5 text-[clamp(1.9rem,3.6vw,3rem)] font-extrabold leading-[1.05] tracking-[-0.03em] text-white">
              A hallucination
              <br />
              <span className="text-verdict-block">never becomes an action.</span>
            </h2>
          </Reveal>

          <Reveal delay={0.14}>
            <p className="mt-5 max-w-lg text-[15px] leading-relaxed text-white/60">
              Detecting a bad claim inside one response is table stakes. The hard part is
              that agents act on their own earlier output, several turns later. Taint
              propagates across the conversation, and the tool gate is the place it gets
              cashed in.
            </p>
          </Reveal>

          <div className="mt-9 space-y-3">
            {TRACE.map((step, index) => (
              <Reveal key={step.turn} delay={0.18 + index * 0.07}>
                <GlassCard className="p-4 sm:p-5">
                  <div className="flex items-center gap-3">
                    <span className="grid h-6 w-6 shrink-0 place-items-center rounded-md border border-white/10 bg-white/[0.04] font-mono text-[10px] text-white/55">
                      {index + 1}
                    </span>
                    <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/35">
                      {step.turn}
                    </p>
                    <p className="truncate text-[13px] font-semibold text-white/85">{step.title}</p>
                    <span
                      className="ml-auto shrink-0 rounded-md border px-2 py-1 font-mono text-[9px] uppercase tracking-[0.14em]"
                      style={{
                        color: step.verdictColor,
                        borderColor: `${step.verdictColor}44`,
                        background: `${step.verdictColor}12`,
                      }}
                    >
                      {step.verdict}
                    </span>
                  </div>

                  <pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-words rounded-lg border border-white/[0.06] bg-black/35 px-3 py-2.5 font-mono text-[11.5px] leading-relaxed text-white/75">
                    <code>{step.payload}</code>
                  </pre>

                  <p className="mt-2.5 text-[12px] leading-relaxed text-white/45">{step.note}</p>
                </GlassCard>
              </Reveal>
            ))}
          </div>
        </div>

        <div className="pointer-events-auto lg:pt-24">
          <Reveal delay={0.1}>
            <GlassCard className="p-5 sm:p-6" >
              <div className="flex items-center gap-2.5">
                <GitBranch size={14} className="text-cyber-violet" aria-hidden />
                <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-white/45">
                  Where taint is resolved
                </p>
              </div>
              <p className="mt-3 text-[13px] leading-relaxed text-white/60">
                Against the audit ledger itself. There is deliberately no second,
                unaudited datastore holding provenance — if a value&apos;s history is not
                in the hash-chained ledger, it does not exist as far as the gate is
                concerned.
              </p>
              <p className="mt-3 font-mono text-[10px] text-white/30">
                ledger/taint.py · policy/tool_gate.py · data/tools.yaml
              </p>
            </GlassCard>
          </Reveal>

          <div className="mt-4 space-y-4">
            {DEFENCES.map((defence, index) => {
              const Icon = defence.icon;
              return (
                <Reveal key={defence.title} delay={0.16 + index * 0.08}>
                  <GlassCard className="p-5 sm:p-6">
                    <div className="flex items-center gap-2.5">
                      <Icon size={14} style={{ color: defence.accent }} aria-hidden />
                      <p
                        className="font-mono text-[10px] uppercase tracking-[0.22em]"
                        style={{ color: defence.accent }}
                      >
                        {defence.title}
                      </p>
                    </div>
                    <p className="mt-3 text-[13px] leading-relaxed text-white/60">{defence.body}</p>
                    <p className="mt-3 flex items-start gap-2 border-t border-white/[0.06] pt-3 font-mono text-[10px] leading-relaxed text-white/30">
                      <FileWarning size={11} className="mt-0.5 shrink-0" aria-hidden />
                      {defence.proof}
                    </p>
                  </GlassCard>
                </Reveal>
              );
            })}
          </div>

          <Reveal delay={0.34}>
            <div
              className={cn(
                "pointer-events-auto mt-4 flex items-start gap-3 rounded-xl border border-verdict-block/25",
                "bg-verdict-block/[0.06] p-4"
              )}
            >
              <Ban size={14} className="mt-0.5 shrink-0 text-verdict-block" aria-hidden />
              <p className="text-[12px] leading-relaxed text-white/55">
                A whole-response <span className="font-mono text-verdict-block">BLOCK</span> is
                reserved — a hard-blocked PII category, or a gated tool call. One bad sentence
                gets remediated surgically, never by discarding the answer.
              </p>
            </div>
          </Reveal>
        </div>
      </div>
    </Section>
  );
}
