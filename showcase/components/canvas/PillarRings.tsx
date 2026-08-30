"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

import { PILLARS } from "@/lib/telemetry";
import { viewport } from "@/lib/viewport-store";

/**
 * Five shield rings around the core node — one per responsibility pillar the
 * risk vector actually carries (hallucination, PII, toxicity, bias, policy).
 * Each ring gets its own tilt, radius and drift speed so the assembly reads
 * as an orrery rather than concentric circles.
 */

interface RingSpec {
  radius: number;
  tilt: [number, number, number];
  speed: number;
  color: string;
  label: string;
}

const RINGS: RingSpec[] = PILLARS.map((pillar, i) => ({
  radius: 1.9 + i * 0.24,
  tilt: [
    Math.PI / 2 + (i - 2) * 0.28,
    i * 0.42,
    (i % 2 === 0 ? 1 : -1) * (0.18 + i * 0.07),
  ],
  speed: (i % 2 === 0 ? 1 : -1) * (0.16 + i * 0.045),
  color: pillar.color,
  label: pillar.label,
}));

function Ring({ spec }: { spec: RingSpec }) {
  const ref = useRef<THREE.Group>(null);

  const material = useMemo(
    () =>
      new THREE.MeshBasicMaterial({
        color: new THREE.Color(spec.color),
        transparent: true,
        opacity: 0.3,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      }),
    [spec.color]
  );

  // Eight evenly spaced nodes riding the ring: the visual stand-in for
  // detector probes sitting on that pillar's orbit.
  const nodeAngles = useMemo(() => Array.from({ length: 6 }, (_, i) => (i / 6) * Math.PI * 2), []);

  useFrame((_, delta) => {
    if (!ref.current) return;
    const dt = Math.min(delta, 0.1);
    ref.current.rotation.z += dt * spec.speed * (viewport.reducedMotion ? 0.2 : 1);
  });

  return (
    <group rotation={spec.tilt}>
      <group ref={ref}>
        <mesh>
          <torusGeometry args={[spec.radius, 0.005, 6, 200]} />
          <primitive object={material} attach="material" />
        </mesh>
        {nodeAngles.map((angle, i) => (
          <mesh
            key={i}
            position={[Math.cos(angle) * spec.radius, Math.sin(angle) * spec.radius, 0]}
          >
            <sphereGeometry args={[0.022, 10, 10]} />
            <primitive object={material} attach="material" />
          </mesh>
        ))}
      </group>
    </group>
  );
}

export function PillarRings() {
  return (
    <group>
      {RINGS.map((spec) => (
        <Ring key={spec.label} spec={spec} />
      ))}
    </group>
  );
}
