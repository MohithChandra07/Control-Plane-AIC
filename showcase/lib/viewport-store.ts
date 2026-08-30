/**
 * A tiny mutable singleton shared between the GSAP/DOM world and the
 * react-three-fiber render loop.
 *
 * Deliberately NOT React state: scroll progress and pointer position update
 * every frame, and pushing those through setState would re-render the whole
 * overlay 60+ times a second. GSAP writes into this object, useFrame reads
 * from it, and React only ever re-renders when the *discrete* active section
 * changes (see subscribeSection).
 */

export interface ViewportState {
  /** 0 → 1 across the whole scrollable page. */
  progress: number;
  /** Index of the section currently filling the viewport. */
  section: number;
  /** Normalised pointer, -1 → 1 on both axes, origin at viewport centre. */
  pointerX: number;
  pointerY: number;
  /** Signed, decaying scroll velocity — drives the grid's ripple energy. */
  velocity: number;
  /** True when the OS asks for reduced motion; every animation checks it. */
  reducedMotion: boolean;
}

export const viewport: ViewportState = {
  progress: 0,
  section: 0,
  pointerX: 0,
  pointerY: 0,
  velocity: 0,
  reducedMotion: false,
};

type SectionListener = (section: number) => void;
const sectionListeners = new Set<SectionListener>();

export function setSection(next: number) {
  if (next === viewport.section) return;
  viewport.section = next;
  sectionListeners.forEach((listener) => listener(next));
}

export function subscribeSection(listener: SectionListener) {
  sectionListeners.add(listener);
  return () => {
    sectionListeners.delete(listener);
  };
}
