"use client";

import { useEffect, useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import * as THREE from "three";

import { viewport } from "@/lib/viewport-store";
import { damp } from "@/lib/utils";

/**
 * Centralised camera choreography.
 *
 * One GSAP timeline, scrubbed by ScrollTrigger across the whole page, drives a
 * plain JS proxy object through four keyframes. useFrame then damps the real
 * camera toward that proxy and adds pointer parallax + an idle float on top.
 *
 * The indirection matters: GSAP owns *where the scroll says we should be*, the
 * render loop owns *how we get there*, so scrubbing never fights the inertia
 * and a fast flick still lands smoothly instead of snapping.
 */

interface Keyframe {
  /** Camera position. */
  p: [number, number, number];
  /** Look-at target. */
  t: [number, number, number];
}

const KEYFRAMES: Keyframe[] = [
  // 01 // HERO — head-on, but framed right-of-centre: the look-at target sits
  // left of the node, which pushes the node into the empty half of the layout
  // instead of straight through the headline.
  { p: [0, 0, 8], t: [-2.1, 0.1, 0] },
  // 02 // SCRUTINY — orbit up and right onto the Tier 0/1 pillar rings.
  { p: [4, 2, 5], t: [-0.9, 0.55, 0] },
  // 03 // TAINT ENGINE — push in close on the taint hotspot.
  { p: [-3, -1, 3], t: [-1.5, -0.55, 0.9] },
  // 04 // CONSOLE — pull back and up, looking down the illuminated grid.
  { p: [0, 6, 10], t: [0, -2.4, -1.5] },
];

export function CameraRig() {
  const { camera } = useThree();

  // The scrub target GSAP writes into. Never read by React.
  const rig = useMemo(
    () => ({
      px: KEYFRAMES[0].p[0],
      py: KEYFRAMES[0].p[1],
      pz: KEYFRAMES[0].p[2],
      tx: KEYFRAMES[0].t[0],
      ty: KEYFRAMES[0].t[1],
      tz: KEYFRAMES[0].t[2],
    }),
    []
  );

  const lookTarget = useRef(new THREE.Vector3(...KEYFRAMES[0].t));

  useEffect(() => {
    gsap.registerPlugin(ScrollTrigger);

    const trigger = document.getElementById("scroll-root");
    if (!trigger) return;

    const timeline = gsap.timeline({
      scrollTrigger: {
        trigger,
        start: "top top",
        end: "bottom bottom",
        // A short scrub smooths the scrub itself; Lenis already handles the
        // inertia of the scroll position, this just softens direction changes.
        scrub: 0.8,
      },
      defaults: { ease: "power2.inOut" },
    });

    KEYFRAMES.slice(1).forEach((frame) => {
      timeline.to(rig, {
        px: frame.p[0],
        py: frame.p[1],
        pz: frame.p[2],
        tx: frame.t[0],
        ty: frame.t[1],
        tz: frame.t[2],
        duration: 1,
      });
    });

    // The overlay sections are absolutely-sized by content; measure once the
    // fonts have settled so the trigger's end matches the real page height.
    const refresh = () => ScrollTrigger.refresh();
    const raf = requestAnimationFrame(refresh);

    return () => {
      cancelAnimationFrame(raf);
      timeline.scrollTrigger?.kill();
      timeline.kill();
    };
  }, [rig]);

  useFrame((_, delta) => {
    const dt = Math.min(delta, 0.1);
    const t = performance.now() / 1000;
    const idle = viewport.reducedMotion ? 0 : 1;

    // Pointer parallax and a slow figure-of-eight drift keep the frame alive
    // when the user is not scrolling. Both are offsets on the GSAP target, so
    // they never accumulate or drift the rig off its keyframe.
    const parallaxX = viewport.pointerX * 0.55 * idle;
    const parallaxY = -viewport.pointerY * 0.4 * idle;
    const floatX = Math.sin(t * 0.31) * 0.16 * idle;
    const floatY = Math.cos(t * 0.24) * 0.12 * idle;

    camera.position.x = damp(camera.position.x, rig.px + parallaxX + floatX, 3, dt);
    camera.position.y = damp(camera.position.y, rig.py + parallaxY + floatY, 3, dt);
    camera.position.z = damp(camera.position.z, rig.pz, 3, dt);

    lookTarget.current.x = damp(lookTarget.current.x, rig.tx, 3.4, dt);
    lookTarget.current.y = damp(lookTarget.current.y, rig.ty, 3.4, dt);
    lookTarget.current.z = damp(lookTarget.current.z, rig.tz, 3.4, dt);
    camera.lookAt(lookTarget.current);
  });

  return null;
}
