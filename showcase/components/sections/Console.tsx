"use client";

import { ArrowUpRight, Database, ExternalLink, SlidersHorizontal, Users } from "lucide-react";

import { Section } from "./Section";
import { GlassCard, SectionLabel } from "@/components/ui/Glass";
import { Reveal } from "@/components/ui/Reveal";
import { APPETITE_SOURCE, APPETITE_SWEEP, PILLARS } from "@/lib/telemetry";

const CHART = { width: 460, height: 195, padX: 40, padY: 22 };

function x(appetite: number) {
  const min = APPETITE_SWEEP[0].appetite;
  const max = APPETITE_SWEEP[APPETITE_SWEEP.length - 1].appetite;
  return CHART.padX + ((appetite - min) / (max - min)) * (CHART.width - CHART.padX * 2);
}

function y(fraction: number) {
  return CHART.height - CHART.padY - fraction * (CHART.height - CHART.padY * 2);
}

const MAX_P95 = Math.max(...APPETITE_SWEEP.map((p) => p.p95));

const recallPath = APPETITE_SWEEP.map(
  (p, i) => `${i === 0 ? "M" : "L"}${x(p.appetite).toFixed(1)},${y(p.hallucinationRecall).toFixed(1)}`
).join(" ");

const latencyPath = APPETITE_SWEEP.map(
  (p, i) => `${i === 0 ? "M" : "L"}${x(p.appetite).toFixed(1)},${y(p.p95 / MAX_P95).toFixed(1)}`
).join(" ");

/**
 * Section 04. The showcase's job here is to hand off to the operational console. The
 * console route is intentionally self-contained for this showcase, while the
 * repository's production console remains untouched.
 */
export function ConsoleSection() {
  return (
    <Section id="console" index={3}>
      <div>
        <div className="grid gap-10 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:gap-14">
          <div className="pointer-events-auto">
            <Reveal>
              <SectionLabel index="04">Live Console</SectionLabel>
            </Reveal>

            <Reveal delay={0.08}>
              <h2 className="mt-5 text-[clamp(1.9rem,3.6vw,3rem)] font-extrabold leading-[1.05] tracking-[-0.03em] text-white">
                Every decision,
                <br />
                <span className="bg-gradient-to-r from-cyber-cyan to-cyber-violet bg-clip-text text-transparent">
                  hash-chained and replayable.
                </span>
              </h2>
            </Reveal>

            <Reveal delay={0.14}>
              <p className="mt-5 max-w-lg text-[15px] leading-relaxed text-white/60">
                One append-only ledger row per request, per extracted claim, and per gated
                tool call — each committing to the previous row&apos;s hash, so a
                retroactive edit is detectable. The console is a read surface over exactly
                that table, plus two audited admin writes: risk appetite, and human review.
              </p>
            </Reveal>

            <Reveal delay={0.2}>
              <div className="mt-8 space-y-3">
                {[
                  {
                    icon: SlidersHorizontal,
                    title: "Risk appetite, per tenant",
                    body: "Scales that tenant's own Tier 0/1 thresholds against their configured baseline. Not cosmetic — the sweep beside this shows what it costs and buys.",
                  },
                  {
                    icon: Users,
                    title: "Human review loop",
                    body: "Reviewers agree or disagree on a past decision. Once disagreement crosses the threshold, a recalibration suggestion surfaces — a suggestion, applied by a human, never silently.",
                  },
                  {
                    icon: Database,
                    title: "Audited admin writes",
                    body: "Changing appetite or filing a review writes to the same hash-chained ledger the gateway uses. There is no second, unaudited path to a governance decision.",
                  },
                ].map((item) => {
                  const Icon = item.icon;
                  return (
                    <GlassCard key={item.title} className="flex gap-3.5 p-4">
                      <Icon size={15} className="mt-0.5 shrink-0 text-cyber-cyan" aria-hidden />
                      <div>
                        <p className="text-[13px] font-semibold text-white/85">{item.title}</p>
                        <p className="mt-1 font-mono text-[9.5px] text-white/25">
                  left axis: hallucination recall %. latency series normalised to the
                  sweep&apos;s highest p95 ({MAX_P95.toFixed(2)}ms).
                </p>

                <p className="mt-2.5 text-[12px] leading-relaxed text-white/45">{item.body}</p>
                      </div>
                    </GlassCard>
                  );
                })}
              </div>
            </Reveal>
          </div>

          <div className="pointer-events-auto">
            <Reveal delay={0.12}>
              <GlassCard className="p-5 sm:p-6">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-white/45">
                    Risk appetite sweep
                  </p>
                  <div className="flex items-center gap-4 font-mono text-[10px]">
                    <span className="flex items-center gap-1.5 text-white/50">
                      <span className="h-px w-4 bg-cyber-cyan" aria-hidden />
                      hallucination recall
                    </span>
                    <span className="flex items-center gap-1.5 text-white/50">
                      <span className="h-px w-4 bg-cyber-violet" aria-hidden />
                      p95 latency
                    </span>
                  </div>
                </div>

                <svg
                  viewBox={`0 0 ${CHART.width} ${CHART.height}`}
                  className="mt-4 w-full"
                  role="img"
                  aria-label="Hallucination recall and p95 latency as risk appetite increases from 0.1 to 0.9"
                >
                  {[0, 0.25, 0.5, 0.75, 1].map((tick) => (
                    <g key={tick}>
                      <line
                        x1={CHART.padX}
                        x2={CHART.width - CHART.padX}
                        y1={y(tick)}
                        y2={y(tick)}
                        stroke="rgba(255,255,255,0.07)"
                        strokeWidth={1}
                      />
                      {/* Left axis is the recall scale; the latency series is
                          normalised against the sweep's own maximum p95, which
                          is stated under the chart so the shape is not mistaken
                          for an absolute reading. */}
                      <text
                        x={CHART.padX - 7}
                        y={y(tick) + 3}
                        textAnchor="end"
                        className="fill-white/30"
                        style={{ fontSize: 8.5, fontFamily: "var(--font-mono)" }}
                      >
                        {(tick * 100).toFixed(0)}
                      </text>
                    </g>
                  ))}

                  <path d={latencyPath} fill="none" stroke="#8b5cf6" strokeWidth={1.6} strokeDasharray="4 3" />
                  <path d={recallPath} fill="none" stroke="#00f0ff" strokeWidth={2} />

                  {APPETITE_SWEEP.map((point) => (
                    <g key={point.appetite}>
                      <circle cx={x(point.appetite)} cy={y(point.hallucinationRecall)} r={3} fill="#00f0ff" />
                      <circle cx={x(point.appetite)} cy={y(point.p95 / MAX_P95)} r={2.4} fill="#8b5cf6" />
                      <text
                        x={x(point.appetite)}
                        y={CHART.height - 5}
                        textAnchor="middle"
                        className="fill-white/35"
                        style={{ fontSize: 9, fontFamily: "var(--font-mono)" }}
                      >
                        {point.appetite.toFixed(1)}
                      </text>
                    </g>
                  ))}
                </svg>

                <p className="mt-1 font-mono text-[9.5px] text-white/25">
                  left axis: hallucination recall %. latency series normalised to the
                  sweep&apos;s highest p95 ({MAX_P95.toFixed(2)}ms).
                </p>

                <p className="mt-2.5 text-[12px] leading-relaxed text-white/45">
                  Recall climbs from{" "}
                  <span className="font-mono text-white/70">22.2%</span> at appetite 0.10 to{" "}
                  <span className="font-mono text-verdict-allow">100%</span> at 0.70, and then
                  flattens — past that point stricter settings buy nothing and only cost
                  escalations.
                </p>

                <p className="mt-3 border-t border-white/[0.06] pt-3 font-mono text-[10px] text-white/30">
                  {APPETITE_SOURCE}
                </p>
              </GlassCard>
            </Reveal>

            <Reveal delay={0.2}>
              <GlassCard className="mt-4 p-5 sm:p-6">
                <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-white/45">
                  Risk vector — five labels per claim
                </p>
                <p className="mt-3 text-[12px] leading-relaxed text-white/50">
                  One claim can carry several at once. An invented phone number is a
                  hallucination <em className="not-italic text-white/75">and</em> a PII hit, and
                  the strongest remediation wins.
                </p>
                <ul className="mt-4 flex flex-wrap gap-2">
                  {PILLARS.map((pillar) => (
                    <li
                      key={pillar.key}
                      className="rounded-lg border px-2.5 py-1.5 font-mono text-[10px] uppercase tracking-[0.12em]"
                      style={{
                        color: pillar.color,
                        borderColor: `${pillar.color}33`,
                        background: `${pillar.color}0f`,
                      }}
                    >
                      {pillar.label}
                    </li>
                  ))}
                </ul>
              </GlassCard>
            </Reveal>

            <Reveal delay={0.26}>
              <a
                href="https://github.com/MohithChandra07/Control-Plane-AIC#running-the-console"
                target="_blank"
                rel="noreferrer noopener"
                className="pointer-events-auto group mt-4 flex items-center justify-between gap-3 rounded-xl border border-cyber-cyan/25 bg-cyber-cyan/[0.06] px-5 py-4 transition-all hover:bg-cyber-cyan/[0.12] hover:shadow-neon"
              >
                <span>
                  <span className="block font-mono text-[11px] uppercase tracking-[0.18em] text-cyber-cyan">
                    Run the governance console
                  </span>
                  <span className="mt-1 block font-mono text-[10px] text-white/40">
                    console/backend + console/frontend — real ledger, no demo data
                  </span>
                </span>
                <ArrowUpRight
                  size={16}
                  aria-hidden
                  className="shrink-0 text-cyber-cyan transition-transform duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5"
                />
              </a>
            </Reveal>
          </div>
        </div>

        <Reveal delay={0.3}>
          <div className="pointer-events-auto mt-6 flex flex-wrap gap-3">
            <a href="/console" className="inline-flex items-center gap-2 rounded-xl border border-white/[0.14] bg-[#121927] px-5 py-3 font-mono text-[11px] uppercase tracking-[0.18em] text-white/80 transition-colors hover:border-white/[0.24] hover:bg-[#182033] hover:text-white">
              Open Control Console <ExternalLink size={14} aria-hidden />
            </a>
          </div>
        </Reveal>

        <Reveal delay={0.1}>
          <footer className="pointer-events-auto mt-20 flex flex-wrap items-center justify-between gap-4 border-t border-white/[0.07] pt-6">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/30">
              ControlPlane.ai — AI Governance &amp; Safety Gateway
            </p>
            <p className="font-mono text-[10px] text-white/25">
              Every figure on this page is transcribed from a committed benchmark artefact.
            </p>
          </footer>
        </Reveal>
      </div>
    </Section>
  );
}
