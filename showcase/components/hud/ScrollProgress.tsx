"use client";

import { useEffect, useState } from "react";

import { scrollToSection } from "@/components/providers/SmoothScroll";
import { subscribeSection, viewport } from "@/lib/viewport-store";
import { cn } from "@/lib/utils";

export const SECTION_LABELS = ["HERO", "SCRUTINY", "TAINT ENGINE", "CONSOLE", "GATEWAY DEMO"] as const;

/**
 * The fixed vertical rail. Subscribes to the *discrete* section change rather
 * than raw scroll progress, so this re-renders roughly four times per visit
 * instead of once per frame; the continuous fill is driven by a rAF loop that
 * writes a CSS custom property and never touches React state at all.
 */
export function ScrollProgress() {
  const [active, setActive] = useState(0);
  const [progress, setProgress] = useState(0);

  useEffect(() => subscribeSection(setActive), []);

  useEffect(() => {
    let frame = 0;
    let last = -1;
    const loop = () => {
      // Quantised to 0.5% so we only re-render on visible change.
      const next = Math.round(viewport.progress * 200) / 200;
      if (next !== last) {
        last = next;
        setProgress(next);
      }
      frame = requestAnimationFrame(loop);
    };
    frame = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(frame);
  }, []);

  return (
    <nav
      aria-label="Section progress"
      className="pointer-events-none fixed left-4 top-1/2 z-30 hidden -translate-y-1/2 lg:block"
    >
      <div className="flex items-stretch gap-3">
        <div className="relative w-px shrink-0 bg-white/10">
          <span
            className="absolute left-0 top-0 w-px bg-gradient-to-b from-cyber-cyan to-cyber-violet shadow-[0_0_10px_rgba(0,240,255,0.8)]"
            style={{ height: `${Math.min(progress * 100, 100)}%` }}
          />
        </div>

        <ul className="pointer-events-auto flex flex-col justify-between gap-5">
          {SECTION_LABELS.map((label, index) => {
            const isActive = index === active;
            return (
              <li key={label}>
                <button
                  type="button"
                  onClick={() => scrollToSection(index)}
                  aria-current={isActive ? "true" : undefined}
                  className="group flex items-center gap-2.5 text-left"
                >
                  <span
                    className={cn(
                      "h-1.5 w-1.5 rounded-full transition-all duration-300",
                      isActive
                        ? "scale-125 bg-cyber-cyan shadow-[0_0_12px_rgba(0,240,255,0.9)]"
                        : "bg-white/25 group-hover:bg-white/60"
                    )}
                  />
                  <span
                    className={cn(
                      "font-mono text-[10px] uppercase tracking-[0.2em] transition-colors duration-300",
                      isActive ? "text-white" : "text-white/35 group-hover:text-white/70"
                    )}
                  >
                    {String(index + 1).padStart(2, "0")} <span className="text-white/20">//</span>{" "}
                    {label}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </nav>
  );
}
