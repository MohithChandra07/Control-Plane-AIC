"use client";

import { useState } from "react";
import { ArrowDownRight, Cpu, ExternalLink, Gauge, MousePointerClick, ShieldCheck } from "lucide-react";

import { Section } from "./Section";
import { GlassCard, SectionLabel } from "@/components/ui/Glass";
import { Reveal } from "@/components/ui/Reveal";
import { RequestDemoModal } from "@/components/ui/RequestDemoModal";
import { DECISIONS } from "@/lib/telemetry";
import { scrollToSection } from "@/components/providers/SmoothScroll";

const PILLARS = [
  {
    icon: Gauge,
    title: "Performance",
    body: "Is the answer reliable? Every claim is extracted and checked against a real corpus.",
  },
  {
    icon: ShieldCheck,
    title: "Cost",
    body: "Is the answer efficient? Token volume, latency and retries stay inside a per-tenant budget.",
  },
  {
    icon: Cpu,
    title: "Responsibility",
    body: "Is the answer safe? PII, prompt injection and tainted tool calls are caught before they ship.",
  },
] as const;

export function Hero() {
  const [demoOpen, setDemoOpen] = useState(false);

  return (
    <Section id="hero" index={0}>
      <div className="pointer-events-auto max-w-2xl">
        <Reveal>
          <SectionLabel index="01">Hero</SectionLabel>
        </Reveal>

        <Reveal delay={0.08}>
          <h1 className="mt-6 text-[clamp(2.6rem,6.2vw,5rem)] font-extrabold leading-[0.98] tracking-[-0.035em] text-white">
            Policy decides.
            <br />
            <span className="bg-gradient-to-r from-cyber-cyan via-white to-cyber-violet bg-clip-text text-transparent">
              Not the model.
            </span>
          </h1>
        </Reveal>

        <Reveal delay={0.16}>
          <p className="mt-7 max-w-xl text-[15px] leading-relaxed text-white/60 sm:text-base">
            ControlPlane sits between your application and the model. It inspects what
            goes in and what comes out, verifies every claim against a real corpus, and
            lets a tenant policy — not silent model behaviour — decide whether a response
            or an agent&apos;s tool call is allowed, modified, escalated, or blocked.
          </p>
        </Reveal>

        <Reveal delay={0.24}>
          <div className="mt-8 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {DECISIONS.map((decision) => (
              <GlassCard key={decision.key} className="p-3.5" title={decision.note}>
                <span
                  className="block h-px w-6"
                  style={{ background: decision.color }}
                  aria-hidden
                />
                <p
                  className="mt-2.5 font-mono text-[11px] font-semibold uppercase tracking-[0.16em]"
                  style={{ color: decision.color }}
                >
                  {decision.key}
                </p>
                <p className="mt-1.5 text-[11px] leading-snug text-white/45">{decision.note}</p>
              </GlassCard>
            ))}
          </div>
        </Reveal>

        <Reveal delay={0.28}>
          <div className="mt-9 grid grid-cols-1 gap-2.5 sm:grid-cols-3">
            {PILLARS.map((pillar) => {
              const Icon = pillar.icon;
              return (
                <GlassCard key={pillar.title} className="p-3.5">
                  <Icon size={14} className="text-cyber-cyan" aria-hidden />
                  <p className="mt-2 text-[12px] font-semibold text-white/85">{pillar.title}</p>
                  <p className="mt-1 text-[11px] leading-snug text-white/45">{pillar.body}</p>
                </GlassCard>
              );
            })}
          </div>
        </Reveal>

        <Reveal delay={0.32}>
          <div className="mt-9 flex flex-wrap items-center gap-3">
            <a
              href="/console"
              className="pointer-events-auto inline-flex items-center gap-2 rounded-xl border border-cyber-cyan/30 bg-cyber-cyan/[0.08] px-5 py-3 font-mono text-[11px] uppercase tracking-[0.18em] text-cyber-cyan transition-all hover:bg-cyber-cyan/[0.15] hover:shadow-neon"
            >
              <ShieldCheck size={14} aria-hidden />
              Launch console
              <ExternalLink size={13} aria-hidden />
            </a>

            <button
              type="button"
              onClick={() => scrollToSection(1)}
              className="pointer-events-auto group inline-flex items-center gap-2 rounded-xl border border-white/[0.14] bg-[#121927] px-5 py-3 font-mono text-[11px] uppercase tracking-[0.18em] text-white/80 transition-colors hover:border-white/[0.24] hover:bg-[#182033] hover:text-white"
            >
              See how it works
              <ArrowDownRight
                size={14}
                aria-hidden
                className="transition-transform duration-300 group-hover:translate-x-0.5 group-hover:translate-y-0.5"
              />
            </button>

            <button
              type="button"
              onClick={() => setDemoOpen(true)}
              className="pointer-events-auto rounded-xl border border-white/[0.1] px-5 py-3 font-mono text-[11px] uppercase tracking-[0.18em] text-white/60 transition-colors hover:border-white/[0.2] hover:text-white"
            >
              Request demo
            </button>

            <span className="inline-flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.16em] text-white/30">
              <MousePointerClick size={12} aria-hidden />
              Hover the nodes in the field
            </span>
          </div>
        </Reveal>
      </div>

      <RequestDemoModal open={demoOpen} onClose={() => setDemoOpen(false)} />
    </Section>
  );
}
