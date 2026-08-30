"use client";

import { useEffect } from "react";
import Lenis from "@studio-freight/lenis";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

import { setSection, viewport } from "@/lib/viewport-store";

/** Set while the provider is mounted so scrollToSection can drive Lenis
 *  directly; native scrollIntoView would fight the inertia layer. */
let activeLenis: Lenis | null = null;

/**
 * Inertia scrolling, and the single place scroll state enters the app.
 *
 * Lenis owns the scroll position; GSAP's ticker drives its RAF so ScrollTrigger
 * and Lenis step in the same frame (running two independent RAF loops is what
 * causes the classic one-frame jitter between pinned DOM and canvas). Every
 * scroll event writes into the viewport singleton rather than React state.
 */
export function SmoothScroll({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    gsap.registerPlugin(ScrollTrigger);

    const reduceQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    viewport.reducedMotion = reduceQuery.matches;
    const onReduceChange = (event: MediaQueryListEvent) => {
      viewport.reducedMotion = event.matches;
    };
    reduceQuery.addEventListener("change", onReduceChange);

    const lenis = new Lenis({
      duration: viewport.reducedMotion ? 0.1 : 1.15,
      easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: !viewport.reducedMotion,
      touchMultiplier: 1.6,
    });

    // Cached so the scroll handler is not querying the DOM every frame.
    let sections: HTMLElement[] = [];
    const collectSections = () => {
      sections = Array.from(document.querySelectorAll<HTMLElement>("[data-section-index]"));
    };
    collectSections();

    /**
     * The section that owns the viewport's centre line. Deterministic — exactly
     * one section can contain a given y — where an IntersectionObserver band
     * reports every overlapping section and leaves the choice ambiguous.
     */
    const updateActiveSection = () => {
      const centre = window.innerHeight / 2;
      for (const element of sections) {
        const rect = element.getBoundingClientRect();
        if (rect.top <= centre && rect.bottom >= centre) {
          const index = Number(element.getAttribute("data-section-index"));
          if (!Number.isNaN(index)) setSection(index);
          return;
        }
      }
    };

    lenis.on("scroll", (event: { progress: number; velocity: number }) => {
      viewport.progress = event.progress;
      // Normalised so the grid shader gets a comparable value across devices
      // whose wheel deltas differ by an order of magnitude.
      viewport.velocity = event.velocity / 24;
      updateActiveSection();
      ScrollTrigger.update();
    });

    updateActiveSection();
    window.addEventListener("resize", collectSections);

    activeLenis = lenis;

    const tick = (time: number) => lenis.raf(time * 1000);
    gsap.ticker.add(tick);
    gsap.ticker.lagSmoothing(0);

    // Velocity has to decay on its own: Lenis stops emitting once the scroll
    // settles, so without this the ripple would stay energised forever.
    const decay = window.setInterval(() => {
      viewport.velocity *= 0.86;
      if (Math.abs(viewport.velocity) < 0.001) viewport.velocity = 0;
    }, 50);

    return () => {
      reduceQuery.removeEventListener("change", onReduceChange);
      window.clearInterval(decay);
      window.removeEventListener("resize", collectSections);
      gsap.ticker.remove(tick);
      activeLenis = null;
      lenis.destroy();
    };
  }, []);

  return <>{children}</>;
}

/** Scrolls to a section by index; used by the HUD progress rail. */
export function scrollToSection(index: number) {
  const target = document.querySelector<HTMLElement>(`[data-section-index="${index}"]`);
  if (!target) return;
  if (activeLenis) {
    activeLenis.scrollTo(target, { offset: 0, duration: 1.3 });
    return;
  }
  target.scrollIntoView({ behavior: "smooth", block: "start" });
}
