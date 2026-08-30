"use client";

import { useState } from "react";
import { Ban, CheckCircle2, CircleHelp, Layers3, TriangleAlert } from "lucide-react";

import { Section } from "./Section";
import { GlassCard, SectionLabel } from "@/components/ui/Glass";
import { Reveal } from "@/components/ui/Reveal";
import { cn } from "@/lib/utils";
import { GATEWAY_SCENARIOS, type DemoDecision, type StageStatus } from "@/lib/demoScenarios";

const DECISION_COLOR: Record<DemoDecision, string> = {
  ALLOW: "#10b981",
  MODIFY: "#3b82f6",
  ESCALATE: "#f59e0b",
  BLOCK: "#ef4444",
};

const STATUS_META: Record<StageStatus, { icon: typeof CheckCircle2; color: string; label: string }> = {
  pass: { icon: CheckCircle2, color: "#10b981", label: "Clear" },
  flag: { icon: TriangleAlert, color: "#f59e0b", label: "Flagged" },
  block: { icon: Ban, color: "#ef4444", label: "Blocked" },
};

/**
 * Section 05 — the interactive gateway demo (spec §7).
 *
 * Every outcome below is precomputed from the real tenant policy it cites
 * (see lib/demoScenarios.ts) rather than a live provider call — there is no
 * upstream model key in a static showcase deploy. The point being
 * demonstrated is real: the same request produces a different decision
 * under a different tenant's configs/*.yaml, driven by policy/engine.py,
 * never re-implemented here.
 */
export function GatewayDemo() {
  const [activeId, setActiveId] = useState(GATEWAY_SCENARIOS[0].id);
  const scenario = GATEWAY_SCENARIOS.find((s) => s.id === activeId) ?? GATEWAY_SCENARIOS[0];
  const decisionColor = DECISION_COLOR[scenario.decision];

  return (
    <Section id="gateway-demo" index={4}>
      <div className="pointer-events-auto">
        <Reveal>
          <SectionLabel index="05">Interactive Gateway Demo</SectionLabel>
        </Reveal>

        <Reveal delay={0.08}>
          <h2 className="mt-5 max-w-2xl text-[clamp(1.9rem,3.6vw,3rem)] font-extrabold leading-[1.05] tracking-[-0.03em] text-white">
            One request. Three tenants.
            <br />
            Three different decisions.
          </h2>
        </Reveal>

        <Reveal delay={0.14}>
          <p className="mt-5 max-w-2xl text-[15px] leading-relaxed text-white/60">
            ControlPlane sits between the application and the model, model-agnostic —
            <span className="font-mono text-white/75"> application → controlplane → model A / B / C / D</span>.
            Pick a tenant profile to see the same request walk through performance, cost and
            responsibility checks, adaptive scrutiny, and the policy engine — each stage citing the
            real YAML field that drove it.
          </p>
        </Reveal>

        <Reveal delay={0.2}>
          <div className="mt-8 flex flex-wrap gap-2">
            {GATEWAY_SCENARIOS.map((s) => {
              const active = s.id === activeId;
              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => setActiveId(s.id)}
                  className={cn(
                    "rounded-xl border px-4 py-3 text-left transition-colors",
                    active
                      ? "border-cyber-cyan/40 bg-cyber-cyan/[0.08]"
                      : "border-white/[0.09] bg-white/[0.02] hover:border-white/[0.18]"
                  )}
                >
                  <p
                    className={cn(
                      "font-mono text-[10px] uppercase tracking-[0.14em]",
                      active ? "text-cyber-cyan" : "text-white/45"
                    )}
                  >
                    {s.tenantLabel}
                  </p>
                  <p className="mt-1 max-w-[220px] text-[12px] leading-snug text-white/70">{s.prompt}</p>
                </button>
              );
            })}
          </div>
        </Reveal>

        <Reveal delay={0.26}>
          <GlassCard className="mt-6 p-5 sm:p-6">
            <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)] lg:gap-8">
              <div>
                <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-white/45">Request</p>
                <p className="mt-2 text-[13px] leading-relaxed text-white/80">{scenario.prompt}</p>

                <p className="mt-4 font-mono text-[10px] uppercase tracking-[0.22em] text-white/45">
                  Model response
                </p>
                <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-words rounded-lg border border-white/[0.06] bg-black/35 px-3 py-2.5 font-mono text-[11.5px] leading-relaxed text-white/75">
                  <code>{scenario.responseExcerpt}</code>
                </pre>

                <p className="mt-4 font-mono text-[10px] uppercase tracking-[0.22em] text-white/45">
                  Tenant policy
                </p>
                <p className="mt-2 font-mono text-[11px] text-white/55">{scenario.configFile}</p>

                <div
                  className="mt-6 flex items-center gap-3 rounded-xl border p-4"
                  style={{ borderColor: `${decisionColor}44`, background: `${decisionColor}12` }}
                >
                  <Layers3 size={16} style={{ color: decisionColor }} aria-hidden />
                  <div>
                    <p
                      className="font-mono text-[13px] font-semibold uppercase tracking-[0.16em]"
                      style={{ color: decisionColor }}
                    >
                      {scenario.decision}
                    </p>
                    <p className="mt-0.5 text-[12px] leading-snug text-white/55">{scenario.decisionNote}</p>
                  </div>
                </div>
              </div>

              <div className="space-y-2.5">
                {scenario.stages.map((stage, index) => {
                  const meta = STATUS_META[stage.status];
                  const Icon = meta.icon;
                  return (
                    <div
                      key={stage.key}
                      className="rounded-xl border border-white/[0.07] bg-white/[0.02] p-3.5"
                    >
                      <div className="flex items-center gap-2.5">
                        <span className="grid h-5 w-5 shrink-0 place-items-center rounded-md border border-white/10 bg-white/[0.04] font-mono text-[9px] text-white/50">
                          {index + 1}
                        </span>
                        <p className="text-[12.5px] font-semibold text-white/85">{stage.label}</p>
                        <span
                          className="ml-auto flex shrink-0 items-center gap-1.5 rounded-md border px-2 py-1 font-mono text-[9px] uppercase tracking-[0.12em]"
                          style={{ color: meta.color, borderColor: `${meta.color}44`, background: `${meta.color}12` }}
                        >
                          <Icon size={11} aria-hidden />
                          {meta.label}
                        </span>
                      </div>
                      <p className="mt-2 text-[12px] leading-relaxed text-white/60">{stage.readout}</p>
                      <p className="mt-1.5 font-mono text-[10px] text-white/30">{stage.citation}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          </GlassCard>
        </Reveal>

        <Reveal delay={0.32}>
          <p className="mt-4 flex items-start gap-2 font-mono text-[10px] leading-relaxed text-white/30">
            <CircleHelp size={12} className="mt-0.5 shrink-0" aria-hidden />
            Illustrative walkthrough: each stage is read off the real tenant policy named beside it, not
            a live model call. A production request runs this same decision once, for real, in
            gateway/routes/chat.py and policy/engine.py.
          </p>
        </Reveal>
      </div>
    </Section>
  );
}
