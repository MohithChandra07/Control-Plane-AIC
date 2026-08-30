"use client";

import { useMemo } from "react";
import {
  Bloom,
  ChromaticAberration,
  EffectComposer,
  Noise,
  Vignette,
} from "@react-three/postprocessing";
import { BlendFunction } from "postprocessing";
import * as THREE from "three";

/**
 * The grade. Bloom does the heavy lifting (every material is additive and
 * unlit, so bloom is what turns "bright lines" into "emissive"); the rest is
 * deliberately restrained — enough film grain and edge falloff to kill the
 * clean-CG look without becoming an effect reel.
 */
export function Effects() {
  const aberrationOffset = useMemo(() => new THREE.Vector2(0.0006, 0.0009), []);

  return (
    <EffectComposer multisampling={0}>
      <Bloom
        intensity={0.62}
        luminanceThreshold={0.32}
        luminanceSmoothing={0.28}
        mipmapBlur
        radius={0.62}
      />
      <ChromaticAberration
        offset={aberrationOffset}
        radialModulation={false}
        modulationOffset={0}
        blendFunction={BlendFunction.NORMAL}
      />
      <Noise opacity={0.035} blendFunction={BlendFunction.OVERLAY} />
      <Vignette eskil={false} offset={0.2} darkness={0.95} />
    </EffectComposer>
  );
}
