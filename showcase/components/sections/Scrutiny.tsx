"use client";

import { Activity, Layers, Timer } from "lucide-react";

import { Section } from "./Section";
import { GlassCard, SectionLabel, Stat } from "@/components/ui/Glass";
import { Reveal } from "@/components/ui/Reveal";
import { BENCH_SOURCE, SCRUTINY_MODES } from "@/lib/telemetry";
import { cn } from "@/lib/utils";

const MAX_P95 = Math.max(...SCRUTINY_MODES.map((mode) => mode.p95));

function pct(value: number | null) {
  return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}

function Bar({
  caption,
  fraction,
  readout,
  color,
}: {
  caption: string;
  fraction: number;
  readout: string;
  color: string;
}) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="w-9 shrink-0 font-mono text-[9px] uppercase tracking-[0.12em] text-white/30">
        {caption}
      </span>
      <span className="h-1 flex-1 overflow-hidden rounded-full bg-white/[0.07]">
        <span
          className="block h-full rounded-full transition-[width] duration-700"
          style={{
            width: `${Math.max(fraction * 100, 1.5)}%`,
            background: color,
            boxShadow: `0 0 10px -2px ${color}`,
          }}
        />
      </span>
      <span className="w-14 shrink-0 text-right font-mono text-[10px] tabular-nums text-white/55">
        {readout}
      </span>
    </div>
  );
}

/**
 * Section 02. The whole argument of adaptive scrutiny is a tradeoff curve, so
 * this shows all three measured configurations side by side rather than
 * quoting only the flattering one — ALWAYS_SHALLOW's 0% recall included.
 */
export function Scrutiny() {
  return (
    <Section id="scrutiny" index={1}>
      <div className="grid gap-10 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:items-center lg:gap-14">
        <div className="pointer-events-auto">
          <Reveal>
            <SectionLabel index="02">Adaptive Scrutiny</SectionLabel>
          </Reveal>

          <Reveal delay={0.08}>
            <h2 className="mt-5 text-[clamp(1.9rem,3.6vw,3rem)] font-extrabold leading-[1.05] tracking-[-0.03em] text-white">
              Depth is earned,
              <br />
              not spent uniformly.
            </h2>
          </Reveal>

          <Reveal delay={0.14}>
            <p className="mt-5 max-w-lg text-[15px] leading-relaxed text-white/60">
              A cheap Tier 0 gate scores every response first. Most traffic never needs
              more than that. Only what crosses the tenant&apos;s{" "}
              <code className="rounded bg-white/[0.06] px-1.5 py-0.5 font-mono text-[12px] text-cyber-cyan">
                tier1_trigger
              </code>{" "}
              pays for claim extraction, corpus verification, PII scanning and the full
              five-label risk vector.
            </p>
          </Reveal>

          <Reveal delay={0.2}>
            <div className="mt-8 grid grid-cols-3 gap-4">
              <Stat
                value="1.71"
                unit="ms"
                label="Tier 0 p50"
                accent="#00f0ff"
                source="benchmark_results.json → ALWAYS_SHALLOW.latency_ms.p50"
              />
              <Stat
                value="69.5"
                unit="%"
                label="Reach Tier 1"
                accent="#8b5cf6"
                source="benchmark_results.json → ADAPTIVE.tier1_invocation_rate"
              />
              <Stat
                value="99.4"
                unit="%"
                label="Hallu. recall"
                accent="#10b981"
                source="benchmark_results.json → ADAPTIVE.hallucination_detection.recall"
              />
            </div>
          </Reveal>

          <Reveal delay={0.26}>
            <p className="mt-7 flex items-start gap-2 font-mono text-[10px] leading-relaxed text-white/30">
              <Layers size={12} className="mt-0.5 shrink-0" aria-hidden />
              {BENCH_SOURCE}
            </p>
          </Reveal>
        </div>

        <Reveal delay={0.12}>
          <GlassCard className="p-5 sm:p-6">
            <div className="flex items-center justify-between">
              <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-white/45">
                Scrutiny configurations
              </p>
              <span className="flex items-center gap-1.5 font-mono text-[10px] text-white/30">
                <Timer size={11} aria-hidden />
                measured
              </span>
            </div>

            <div className="mt-5 space-y-4">
              {SCRUTINY_MODES.map((mode) => {
                const isAdaptive = mode.mode === "ADAPTIVE";
                return (
                  <div
                    key={mode.mode}
                    className={cn(
                      "rounded-xl border p-4 transition-colors duration-500",
                      isAdaptive
                        ? "border-cyber-cyan/30 bg-cyber-cyan/[0.05]"
                        : "border-white/[0.07] bg-white/[0.02]"
                    )}
                  >
                    <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
                      <p
                        className={cn(
                          "font-mono text-[12px] font-semibold tracking-[0.12em]",
                          isAdaptive ? "text-cyber-cyan" : "text-white/70"
                        )}
                      >
                        {mode.mode}
                      </p>
                      <p className="font-mono text-[11px] tabular-nums text-white/45">
                        p50 {mode.p50.toFixed(2)}ms · p95 {mode.p95.toFixed(2)}ms
                      </p>
                    </div>

                    <p className="mt-1.5 text-[12px] leading-snug text-white/45">{mode.blurb}</p>

                    {/* Two bars on a shared scale: recall as a fraction of 1.0,
                        latency as a fraction of the slowest measured p95. Read
                        together they are the tradeoff — the first row buys its
                        speed with an empty recall bar. */}
                    <div className="mt-3 space-y-1.5">
                      <Bar
                        caption="recall"
                        fraction={mode.hallucinationRecall ?? 0}
                        readout={pct(mode.hallucinationRecall)}
                        color="#00f0ff"
                      />
                      <Bar
                        caption="p95"
                        fraction={mode.p95 / MAX_P95}
                        readout={`${mode.p95.toFixed(2)}ms`}
                        color="#8b5cf6"
                      />
                    </div>

                    <dl className="mt-3 grid grid-cols-3 gap-2 font-mono text-[10px]">
                      <div>
                        <dt className="text-white/30">Tier 1 rate</dt>
                        <dd className="mt-0.5 tabular-nums text-white/70">{pct(mode.tier1Rate)}</dd>
                      </div>
                      <div>
                        <dt className="text-white/30">PII recall</dt>
                        <dd className="mt-0.5 tabular-nums text-white/70">{pct(mode.piiRecall)}</dd>
                      </div>
                      <div>
                        <dt className="text-white/30">ECE</dt>
                        <dd className="mt-0.5 tabular-nums text-white/70">
                          {mode.ece === null ? "n/a" : mode.ece.toFixed(3)}
                        </dd>
                      </div>
                    </dl>
                  </div>
                );
              })}
            </div>

            <p className="mt-4 flex items-start gap-2 border-t border-white/[0.06] pt-4 font-mono text-[10px] leading-relaxed text-white/30">
              <Activity size={12} className="mt-0.5 shrink-0" aria-hidden />
              ALWAYS_SHALLOW is the honest floor: fastest possible, and it catches
              nothing. That row is why adaptive scrutiny exists.
            </p>
          </GlassCard>
        </Reveal>
      </div>
    </Section>
  );
}
