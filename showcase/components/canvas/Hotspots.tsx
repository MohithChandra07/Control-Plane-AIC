"use client";

import { useEffect, useRef, useState } from "react";
import { Html } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { Gauge, GitBranch, ShieldAlert, Zap } from "lucide-react";

import { cn } from "@/lib/utils";
import { subscribeSection, viewport } from "@/lib/viewport-store";

export interface Hotspot {
  id: string;
  index: string;
  title: string;
  headline: string;
  body: string;
  metric: string;
  metricSource: string;
  position: [number, number, number];
  accent: string;
  icon: typeof Gauge;
}

/**
 * Spatial markers pinned to the geometry. Copy is drawn from what the gateway
 * actually implements (see gateway/routes/chat.py and policy/tool_gate.py) —
 * these are labels on real subsystems, not feature-marketing.
 */
export const HOTSPOTS: Hotspot[] = [
  {
    id: "scrutiny",
    index: "01",
    title: "Adaptive Scrutiny",
    headline: "Tier 0 gate → Tier 1 deep verification",
    body: "A cheap heuristic gate scores every response first. Only what clears the tenant's tier1_trigger pays for claim extraction, corpus verification and the full risk vector.",
    metric: "1.71 ms p50 at the gate · 69.5% escalated to Tier 1",
    metricSource: "bench/results/benchmark_results.json",
    position: [1.55, 1.35, 0.5],
    accent: "#00f0ff",
    icon: Gauge,
  },
  {
    id: "taint",
    index: "02",
    title: "Multi-Turn Taint Engine",
    headline: "Provenance that survives the turn boundary",
    body: "A claim ControlPlane cannot confirm is marked tainted. When a later turn calls issue_refund(amount=48000) with a value tracing back to it, the gate blocks the call before the application ever sees it.",
    metric: "Taint resolved against the audit ledger itself — no second datastore",
    metricSource: "ledger/taint.py · policy/tool_gate.py",
    position: [-0.35, -1.5, 1.2],
    accent: "#8b5cf6",
    icon: GitBranch,
  },
  {
    id: "injection",
    index: "03",
    title: "Prompt Injection Shield",
    headline: "Untrusted tool output, sanitised pre-flight",
    body: 'Only role="tool" and role="function" messages are scanned — the convention for retrieved content. The matched span alone is replaced; the model never receives the injected instruction, and the legitimate document survives.',
    metric: "Surgical span replacement, never whole-document rejection",
    metricSource: "detectors/injection.py · Scene 4",
    position: [0.35, 1.95, -0.7],
    accent: "#f59e0b",
    icon: ShieldAlert,
  },
  {
    id: "breaker",
    index: "04",
    title: "Cost Circuit Breaker",
    headline: "Trips before the provider call, not after",
    body: "A per-tenant sliding window over request count and token volume. When it trips the upstream call never happens — 429 returned, zero cost incurred, and the trip itself audited with its reason.",
    metric: "Verified: 31 rapid requests, provider called exactly 30 times",
    metricSource: "tests/integration/test_gateway_scenes_5_7.py",
    position: [1.75, -1.35, -0.5],
    accent: "#10b981",
    icon: Zap,
  },
];

/** Matches the w-[19rem] on the callout panel below. */
const CALLOUT_WIDTH = 304;

function Marker({ hotspot, visible }: { hotspot: Hotspot; visible: boolean }) {
  const [open, setOpen] = useState(false);
  const [hovered, setHovered] = useState(false);
  const ring = useRef<THREE.Mesh>(null);
  const Icon = hotspot.icon;

  useFrame(() => {
    if (!ring.current) return;
    const t = performance.now() / 1000;
    const pulse = viewport.reducedMotion ? 1 : 1 + Math.sin(t * 2.2) * 0.16;
    ring.current.scale.setScalar(pulse * (hovered || open ? 1.35 : 1));
  });

  const expanded = visible && (open || hovered);

  return (
    <group position={hotspot.position}>
      <mesh ref={ring}>
        <ringGeometry args={[0.075, 0.1, 32]} />
        <meshBasicMaterial
          color={hotspot.accent}
          transparent
          opacity={0.9}
          side={THREE.DoubleSide}
          toneMapped={false}
        />
      </mesh>
      <mesh>
        <sphereGeometry args={[0.035, 12, 12]} />
        <meshBasicMaterial color={hotspot.accent} toneMapped={false} />
      </mesh>

      <Html
        center={false}
        zIndexRange={[40, 20]}
        style={{ pointerEvents: "none" }}
        calculatePosition={(el, camera, size) => {
          // drei's default puts the element's top-left on the anchor; nudge it
          // clear of the marker so the dot stays visible next to the callout.
          const objectPos = new THREE.Vector3().setFromMatrixPosition(el.matrixWorld);
          objectPos.project(camera);
          const widthHalf = size.width / 2;
          const heightHalf = size.height / 2;
          const x = objectPos.x * widthHalf + widthHalf + 14;
          const y = -(objectPos.y * heightHalf) + heightHalf - 12;
          // The callout is a fixed 304px wide; clamp so a marker near the right
          // edge flips its panel inward rather than running off-screen.
          const maxX = size.width - CALLOUT_WIDTH - 24;
          return [Math.min(Math.max(x, 12), Math.max(maxX, 12)), y];
        }}
      >
        <div
          className={cn(
            "hidden select-none transition-opacity duration-500 lg:block",
            visible ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0"
          )}
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
        >
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={expanded}
            className={cn(
              "flex items-center gap-2 rounded-full border px-3 py-1.5",
              "bg-[rgba(8,11,19,0.82)] backdrop-blur-[16px] transition-all duration-300",
              "font-mono text-[10px] uppercase tracking-[0.18em] text-white/80",
              "hover:text-white"
            )}
            style={{
              borderColor: `${hotspot.accent}55`,
              boxShadow: expanded ? `0 0 26px -6px ${hotspot.accent}` : "none",
            }}
          >
            <Icon size={12} style={{ color: hotspot.accent }} aria-hidden />
            <span style={{ color: hotspot.accent }}>{hotspot.index}</span>
            <span className="whitespace-nowrap">{hotspot.title}</span>
          </button>

          <div
            className={cn(
              "mt-2 w-[19rem] origin-top-left overflow-hidden rounded-xl border",
              "bg-[rgba(15,23,42,0.72)] backdrop-blur-[16px]",
              "transition-all duration-300 ease-out",
              expanded
                ? "max-h-[22rem] translate-y-0 opacity-100"
                : "pointer-events-none max-h-0 -translate-y-1 opacity-0"
            )}
            style={{ borderColor: `${hotspot.accent}33` }}
          >
            <div className="p-4">
              <p
                className="font-mono text-[10px] uppercase tracking-[0.2em]"
                style={{ color: hotspot.accent }}
              >
                {hotspot.headline}
              </p>
              <p className="mt-2.5 text-[13px] leading-relaxed text-white/70">{hotspot.body}</p>
              <div
                className="mt-3 border-t pt-3"
                style={{ borderColor: `${hotspot.accent}22` }}
              >
                <p className="font-mono text-[11px] text-white/85">{hotspot.metric}</p>
                <p className="mt-1 font-mono text-[10px] text-white/35">{hotspot.metricSource}</p>
              </div>
            </div>
          </div>
        </div>
      </Html>
    </group>
  );
}

/**
 * Markers belong to the hero. That is the one section whose layout leaves the
 * right half of the viewport empty for the geometry; from 02 onward the copy
 * uses both columns, and floating pills over those panels would be clutter
 * sitting on top of content that already says the same thing.
 */
const MARKER_SECTIONS = new Set([0]);

export function Hotspots() {
  const [section, setSection] = useState(0);

  useEffect(() => subscribeSection(setSection), []);

  const visible = MARKER_SECTIONS.has(section);

  return (
    <group>
      {HOTSPOTS.map((hotspot) => (
        <Marker key={hotspot.id} hotspot={hotspot} visible={visible} />
      ))}
    </group>
  );
}
