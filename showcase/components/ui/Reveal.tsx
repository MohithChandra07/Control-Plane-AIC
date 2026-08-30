"use client";

import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

import { viewport } from "@/lib/viewport-store";
import { cn } from "@/lib/utils";

/**
 * Scroll-triggered entrance. One ScrollTrigger per Reveal, created inside a
 * gsap.context so React strict-mode's double-mount cleanly reverts the first
 * instance instead of leaving a duplicate trigger behind.
 *
 * Honours prefers-reduced-motion by snapping straight to the final state — the
 * content is never gated behind an animation that may not play.
 */
export function Reveal({
  children,
  delay = 0,
  y = 26,
  className,
}: {
  children: React.ReactNode;
  delay?: number;
  y?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    gsap.registerPlugin(ScrollTrigger);

    if (viewport.reducedMotion) {
      gsap.set(element, { opacity: 1, y: 0 });
      return;
    }

    const context = gsap.context(() => {
      gsap.fromTo(
        element,
        { opacity: 0, y, filter: "blur(6px)" },
        {
          opacity: 1,
          y: 0,
          filter: "blur(0px)",
          duration: 0.9,
          delay,
          ease: "power3.out",
          scrollTrigger: {
            trigger: element,
            start: "top 88%",
            toggleActions: "play none none reverse",
          },
        }
      );
    }, element);

    return () => context.revert();
  }, [delay, y]);

  return (
    <div ref={ref} className={cn("opacity-0", className)}>
      {children}
    </div>
  );
}
