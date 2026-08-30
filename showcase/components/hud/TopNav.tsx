"use client";

import { useState } from "react";
import { Github, Hexagon, Radio, TerminalSquare } from "lucide-react";

import { HEADLINE_METRICS } from "@/lib/telemetry";
import { cn } from "@/lib/utils";
import { scrollToSection } from "@/components/providers/SmoothScroll";
import { RequestDemoModal } from "@/components/ui/RequestDemoModal";

const REPO_URL = "https://github.com/MohithChandra07/Control-Plane-AIC";

const NAV_LINKS = [
  { label: "Platform", section: 0 },
  { label: "How It Works", section: 1 },
  { label: "Governance", section: 2 },
  { label: "Gateway Demo", section: 4 },
] as const;

export function TopNav() {
  const [demoOpen, setDemoOpen] = useState(false);

  return (
    <header className="pointer-events-none fixed inset-x-0 top-0 z-40 px-4 pt-3 sm:px-6">
      <div
        className={cn(
          "pointer-events-auto mx-auto flex max-w-[1400px] items-center gap-2.5",
          "rounded-xl border border-white/[0.09] bg-[#111722] px-3 py-2",
          "shadow-[0_18px_50px_-30px_rgba(0,0,0,0.7)]"
        )}
      >
        <a href="#hero" className="group flex shrink-0 items-center gap-2">
          <span className="relative grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-[#182236] border border-white/[0.08]">
            <Hexagon size={14} className="text-white" strokeWidth={2.4} />
          </span>
          <span className="flex flex-col justify-center leading-none">
            <span className="whitespace-nowrap text-[13.5px] font-extrabold tracking-tight text-white">
              ControlPlane<span className="text-slate-300">.ai</span>
            </span>
            <span className="mt-1 whitespace-nowrap font-mono text-[8.5px] uppercase tracking-[0.16em] text-white/40">
              Governance Gateway
            </span>
          </span>
        </a>

        <div className="hidden shrink-0 items-center gap-1.5 rounded-full border border-verdict-allow/25 bg-verdict-allow/[0.07] px-2 py-1 md:flex">
          <span className="h-1.5 w-1.5 shrink-0 animate-pulse-dot rounded-full bg-verdict-allow" />
          <span className="whitespace-nowrap font-mono text-[9px] uppercase tracking-[0.08em] text-verdict-allow/90">
            Live Stream Connected
          </span>
        </div>

        <nav className="hidden items-center gap-2.5 lg:flex" aria-label="Primary">
          {NAV_LINKS.map((link) => (
            <button
              key={link.label}
              type="button"
              onClick={() => scrollToSection(link.section)}
              className="whitespace-nowrap font-mono text-[10px] uppercase tracking-[0.08em] text-white/50 transition-colors hover:text-white"
            >
              {link.label}
            </button>
          ))}
        </nav>

        {/* Full telemetry strip only once there's genuinely room for it
            alongside nav + CTAs within the header's own max-w-[1400px] —
            below that, the compact wrapped row underneath (already built
            for this) carries the same numbers without competing for this
            row's horizontal space. */}
        <div className="ml-auto hidden shrink-0 items-center divide-x divide-white/[0.08] 2xl:flex">
          {HEADLINE_METRICS.map((metric) => (
            <div
              key={metric.label}
              title={`Source: ${metric.source}`}
              className="group flex shrink-0 cursor-help items-baseline gap-1 whitespace-nowrap px-2 first:pl-0"
            >
              <span className="font-mono text-[8.5px] uppercase tracking-[0.04em] text-white/40 group-hover:text-white/60">
                {metric.label}
              </span>
              <span className="font-mono text-[11px] font-semibold text-cyber-cyan">
                {metric.value}
                {metric.unit ? <span className="text-[9px] text-white/45">{metric.unit}</span> : null}
              </span>
            </div>
          ))}
        </div>

        <div className="ml-auto flex shrink-0 items-center gap-1.5 2xl:ml-2">
          {/* The primary CTA — unlike Console/GitHub below, this stays
              visible at every width the header supports (down to the
              narrowest phones), never gated behind a breakpoint. */}
          <button
            type="button"
            onClick={() => setDemoOpen(true)}
            className="flex items-center whitespace-nowrap rounded-lg border border-white/[0.12] bg-white/[0.03] px-2.5 py-1.5 font-mono text-[10px] uppercase tracking-[0.1em] text-white/70 transition-colors hover:border-white/[0.22] hover:text-white"
          >
            Request Demo
          </button>
          <a
            href="/console"
            className={cn(
              "hidden items-center gap-1.5 whitespace-nowrap rounded-lg border border-white/[0.12] bg-[#151e2d]",
              "px-2.5 py-1.5 font-mono text-[10px] uppercase tracking-[0.1em] text-cyber-cyan",
              "transition-all hover:bg-[#1a2537] sm:flex"
            )}
          >
            <TerminalSquare size={12} aria-hidden />
            Console
          </a>
          <a
            href={REPO_URL}
            target="_blank"
            rel="noreferrer noopener"
            aria-label="Open the ControlPlane repository on GitHub"
            className="grid h-7 w-7 shrink-0 place-items-center rounded-lg border border-white/[0.08] bg-white/[0.03] text-white/60 transition-colors hover:border-white/20 hover:text-white"
          >
            <Github size={13} aria-hidden />
          </a>
        </div>
      </div>

      <div className="pointer-events-auto mx-auto mt-2 flex max-w-[1400px] items-center gap-2 px-1 2xl:hidden">
        <Radio size={11} className="shrink-0 text-cyber-cyan/70" aria-hidden />
        <div className="flex flex-wrap gap-x-3 gap-y-1">
          {HEADLINE_METRICS.map((metric) => (
            <span key={metric.label} className="font-mono text-[9px] tracking-[0.12em] text-white/45">
              {metric.label.toUpperCase()}{" "}
              <span className="text-cyber-cyan">
                {metric.value}
                {metric.unit ?? ""}
              </span>
            </span>
          ))}
        </div>
      </div>

      <RequestDemoModal open={demoOpen} onClose={() => setDemoOpen(false)} />
    </header>
  );
}
