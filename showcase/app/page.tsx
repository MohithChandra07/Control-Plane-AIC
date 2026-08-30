import dynamic from "next/dynamic";

import { ScrollProgress } from "@/components/hud/ScrollProgress";
import { TopNav } from "@/components/hud/TopNav";
import { SmoothScroll } from "@/components/providers/SmoothScroll";
import { ConsoleSection } from "@/components/sections/Console";
import { GatewayDemo } from "@/components/sections/GatewayDemo";
import { Hero } from "@/components/sections/Hero";
import { Scrutiny } from "@/components/sections/Scrutiny";
import { TaintEngine } from "@/components/sections/TaintEngine";

/**
 * The WebGL layer is client-only: three touches `window` and `document` during
 * module init, and there is nothing meaningful to server-render for a canvas.
 * The DOM overlay below it renders on the server as normal, so the page's
 * content and telemetry are in the initial HTML — crawlable, and readable
 * before (or without) the canvas ever coming up.
 */
const Scene = dynamic(() => import("@/components/canvas/Scene").then((m) => m.Scene), {
  ssr: false,
});

export default function Page() {
  return (
    <SmoothScroll>
      <Scene />

      {/*
        Atmosphere and legibility, in layers between the canvas (z-0) and the
        copy (z-10). The veil and the left scrim are not decoration: additive
        wireframe behind body text is unreadable, and the scrim guarantees a
        dark ground under the copy column at every camera position rather than
        hoping the choreography keeps the geometry out of the way.
      */}
      <div className="pointer-events-none fixed inset-0 z-[3] bg-void/[0.68] lg:bg-void/50" aria-hidden />
      <div
        className="pointer-events-none fixed inset-y-0 left-0 z-[4] hidden w-[62%] bg-gradient-to-r from-void via-void/85 to-transparent lg:block"
        aria-hidden
      />
      <div className="crt-overlay pointer-events-none fixed inset-0 z-[5]" aria-hidden />
      <div
        className="pointer-events-none fixed inset-x-0 top-0 z-[6] h-32 bg-gradient-to-b from-void/85 to-transparent"
        aria-hidden
      />
      <div
        className="pointer-events-none fixed inset-x-0 bottom-0 z-[6] h-24 bg-gradient-to-t from-void/70 to-transparent"
        aria-hidden
      />

      <TopNav />
      <ScrollProgress />

      <main id="scroll-root" className="pointer-events-none relative z-10">
        <Hero />
        <Scrutiny />
        <TaintEngine />
        <ConsoleSection />
        <GatewayDemo />
      </main>
    </SmoothScroll>
  );
}
