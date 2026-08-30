"use client";

import { Suspense, useEffect, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { AdaptiveDpr, AdaptiveEvents, Preload, Stars } from "@react-three/drei";

import { CameraRig } from "./CameraRig";
import { Effects } from "./Effects";
import { GovernanceNode } from "./GovernanceNode";
import { GridFloor } from "./GridFloor";
import { Hotspots } from "./Hotspots";
import { PillarRings } from "./PillarRings";
import { viewport } from "@/lib/viewport-store";

function hasWebGL() {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(
      window.WebGLRenderingContext &&
        (canvas.getContext("webgl2") || canvas.getContext("webgl"))
    );
  } catch {
    return false;
  }
}

/**
 * The fixed, full-viewport WebGL layer. Everything DOM sits above it with
 * pointer-events:none, so the canvas keeps pointer-events:auto and receives
 * the raw mouse move — that is what feeds the grid ripple and the parallax.
 */
export function Scene() {
  const [supported, setSupported] = useState<boolean | null>(null);

  useEffect(() => {
    setSupported(hasWebGL());
  }, []);

  // Tracked on window rather than on the canvas element: the DOM overlay has
  // interactive glass cards sitting on top, and a listener bound to the canvas
  // would go dead the moment the cursor crossed one of them.
  useEffect(() => {
    const onMove = (event: PointerEvent) => {
      viewport.pointerX = (event.clientX / window.innerWidth) * 2 - 1;
      viewport.pointerY = (event.clientY / window.innerHeight) * 2 - 1;
    };
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, []);

  if (supported === false) {
    // Static gradient stand-in. The site is still fully readable without WebGL
    // — the copy and telemetry live in the DOM overlay, not in the canvas.
    return (
      <div
        aria-hidden
        className="fixed inset-0 z-0 bg-[radial-gradient(circle_at_50%_35%,#12203a_0%,#05070c_70%)]"
      />
    );
  }

  return (
    // No aria-hidden here: the drei <Html> hotspots inside the canvas are real
    // interactive content (buttons with text), and hiding the subtree would take
    // them away from assistive tech entirely. The <canvas> itself exposes
    // nothing, so there is no decorative noise to suppress.
    <div className="fixed inset-0 z-0">
      {supported && (
        <Canvas
          camera={{ position: [0, 0, 8], fov: 45, near: 0.1, far: 120 }}
          dpr={[1, 1.75]}
          gl={{
            antialias: true,
            powerPreference: "high-performance",
            alpha: true,
          }}
        >
          <color attach="background" args={["#05070c"]} />
          <fog attach="fog" args={["#05070c", 12, 46]} />

          <ambientLight intensity={0.35} />

          <Suspense fallback={null}>
            <Stars radius={70} depth={40} count={2400} factor={3.2} saturation={0} fade speed={0.4} />
            <GridFloor />
            <GovernanceNode />
            <PillarRings />
            <Hotspots />
            <Preload all />
          </Suspense>

          <CameraRig />
          <Effects />

          {/* Drops resolution rather than frames when the GPU is struggling. */}
          <AdaptiveDpr pixelated />
          <AdaptiveEvents />
        </Canvas>
      )}
    </div>
  );
}
