"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

import { createWireframeMaterial } from "./materials";
import { viewport } from "@/lib/viewport-store";
import { damp } from "@/lib/utils";

/**
 * The Core AI Governance Node: an icosahedral shell wrapped around a torus
 * knot, both drawn as glowing wireframe. The two counter-rotate, which is
 * what stops it reading as a single spinning prop.
 */
export function GovernanceNode() {
  const group = useRef<THREE.Group>(null);
  const shell = useRef<THREE.Mesh>(null);
  const knot = useRef<THREE.Mesh>(null);
  const inner = useRef<THREE.Mesh>(null);

  const shellMaterial = useMemo(() => createWireframeMaterial({ intensity: 0.5 }), []);
  const knotMaterial = useMemo(
    () => createWireframeMaterial({ colorA: "#8b5cf6", colorB: "#00f0ff", intensity: 0.62 }),
    []
  );
  const coreMaterial = useMemo(
    () => createWireframeMaterial({ colorA: "#6366f1", colorB: "#00f0ff", intensity: 0.3 }),
    []
  );

  useFrame((_, delta) => {
    const dt = Math.min(delta, 0.1);
    const t = performance.now() / 1000;
    const slow = viewport.reducedMotion ? 0.15 : 1;

    shellMaterial.uniforms.uTime.value = t;
    knotMaterial.uniforms.uTime.value = t;
    coreMaterial.uniforms.uTime.value = t;

    if (shell.current) {
      shell.current.rotation.y += dt * 0.14 * slow;
      shell.current.rotation.x += dt * 0.05 * slow;
    }
    if (knot.current) {
      knot.current.rotation.z -= dt * 0.22 * slow;
      knot.current.rotation.x += dt * 0.09 * slow;
    }
    if (inner.current) {
      inner.current.rotation.y -= dt * 0.3 * slow;
    }

    // Gentle pointer-follow so the node feels like it is aware of the cursor
    // without ever fully tracking it (that reads as gimmicky).
    if (group.current) {
      group.current.rotation.y = damp(group.current.rotation.y, viewport.pointerX * 0.22, 2.2, dt);
      group.current.rotation.x = damp(group.current.rotation.x, -viewport.pointerY * 0.16, 2.2, dt);
      group.current.position.y = damp(
        group.current.position.y,
        Math.sin(t * 0.6) * (viewport.reducedMotion ? 0.02 : 0.12),
        2.5,
        dt
      );
    }
  });

  return (
    <group ref={group} scale={0.78}>
      <mesh ref={shell}>
        <icosahedronGeometry args={[1.75, 2]} />
        <primitive object={shellMaterial} attach="material" />
      </mesh>

      <mesh ref={knot} scale={0.62}>
        <torusKnotGeometry args={[1.15, 0.3, 168, 18, 2, 3]} />
        <primitive object={knotMaterial} attach="material" />
      </mesh>

      <mesh ref={inner} scale={0.34}>
        <icosahedronGeometry args={[1, 1]} />
        <primitive object={coreMaterial} attach="material" />
      </mesh>

      {/* A single point light inside the shell so Bloom has a hot core to
          bleed from — the wireframe itself is unlit/additive. */}
      <pointLight position={[0, 0, 0]} intensity={3.2} distance={6} color="#00f0ff" />
    </group>
  );
}
