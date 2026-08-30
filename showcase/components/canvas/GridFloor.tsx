"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

import { createGridMaterial } from "./materials";
import { viewport } from "@/lib/viewport-store";
import { damp } from "@/lib/utils";

const SIZE = 46;
const SEGMENTS = 118;

/**
 * The interactive floor: a dense point grid whose vertices are displaced in
 * the vertex shader by an ambient swell plus a ripple centred on the pointer,
 * with scroll velocity feeding the ripple's amplitude.
 *
 * Points rather than a wireframe plane because ~14k additive dots read as a
 * volumetric field, and one draw call keeps it cheap.
 */
export function GridFloor() {
  const material = useMemo(() => createGridMaterial(), []);
  const geometry = useMemo(() => new THREE.PlaneGeometry(SIZE, SIZE, SEGMENTS, SEGMENTS), []);
  const pointer = useRef(new THREE.Vector2(0, 0));

  useFrame((_, delta) => {
    const dt = Math.min(delta, 0.1);
    material.uniforms.uTime.value = performance.now() / 1000;
    material.uniforms.uReduced.value = viewport.reducedMotion ? 1 : 0;

    // The pointer arrives in NDC; map it onto the plane's own local space and
    // damp it so the ripple trails the cursor instead of teleporting.
    const targetX = viewport.pointerX * SIZE * 0.42;
    const targetY = -viewport.pointerY * SIZE * 0.3 - 4;
    pointer.current.x = damp(pointer.current.x, targetX, 3.2, dt);
    pointer.current.y = damp(pointer.current.y, targetY, 3.2, dt);
    material.uniforms.uPointer.value.copy(pointer.current);

    const energy = material.uniforms.uEnergy;
    energy.value = damp(energy.value, Math.min(Math.abs(viewport.velocity) * 0.6, 1.4), 3.5, dt);
  });

  return (
    <points position={[0, -3.4, -2]} rotation={[-Math.PI / 2, 0, 0]}>
      <primitive object={geometry} attach="geometry" />
      <primitive object={material} attach="material" />
    </points>
  );
}
