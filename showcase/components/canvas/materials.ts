import * as THREE from "three";

/**
 * Hand-written GLSL for the two signature materials. Both are plain
 * THREE.ShaderMaterial instances built in a factory rather than declared via
 * drei's `shaderMaterial` + `extend`, so they stay fully typed under
 * `strict: true` without augmenting the JSX intrinsic-element namespace.
 */

const FRESNEL_VERT = /* glsl */ `
  varying vec3 vNormalW;
  varying vec3 vViewDir;
  varying vec3 vPositionL;

  void main() {
    vPositionL = position;
    vec4 worldPosition = modelMatrix * vec4(position, 1.0);
    vNormalW = normalize(mat3(modelMatrix) * normal);
    vViewDir = normalize(cameraPosition - worldPosition.xyz);
    gl_Position = projectionMatrix * viewMatrix * worldPosition;
  }
`;

const FRESNEL_FRAG = /* glsl */ `
  uniform float uTime;
  uniform float uIntensity;
  uniform vec3 uColorA;
  uniform vec3 uColorB;

  varying vec3 vNormalW;
  varying vec3 vViewDir;
  varying vec3 vPositionL;

  void main() {
    // Rim-light term: edges facing away from the camera glow hardest, which
    // is what reads as "energy field" rather than "shaded plastic".
    float fresnel = pow(1.0 - abs(dot(normalize(vNormalW), normalize(vViewDir))), 2.2);

    // A slow band travelling along the model's local Y, so the wireframe
    // looks like it is being scanned rather than statically lit.
    float scan = 0.5 + 0.5 * sin(vPositionL.y * 3.4 - uTime * 1.1);

    vec3 color = mix(uColorA, uColorB, clamp(scan * 0.85 + fresnel * 0.4, 0.0, 1.0));
    float alpha = clamp((0.22 + fresnel * 0.9) * uIntensity, 0.0, 1.0);

    gl_FragColor = vec4(color * (0.7 + fresnel * 1.3), alpha);
  }
`;

export interface WireframeOptions {
  colorA?: THREE.ColorRepresentation;
  colorB?: THREE.ColorRepresentation;
  intensity?: number;
}

export function createWireframeMaterial(options: WireframeOptions = {}) {
  return new THREE.ShaderMaterial({
    vertexShader: FRESNEL_VERT,
    fragmentShader: FRESNEL_FRAG,
    uniforms: {
      uTime: { value: 0 },
      uIntensity: { value: options.intensity ?? 1 },
      uColorA: { value: new THREE.Color(options.colorA ?? "#00f0ff") },
      uColorB: { value: new THREE.Color(options.colorB ?? "#8b5cf6") },
    },
    wireframe: true,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
}

const GRID_VERT = /* glsl */ `
  uniform float uTime;
  uniform vec2 uPointer;
  uniform float uEnergy;
  uniform float uSize;
  uniform float uReduced;

  varying float vElevation;
  varying float vRipple;

  void main() {
    vec3 pos = position;

    // Two travelling swells give the plane a slow ocean-like drift...
    float swell =
      sin(pos.x * 0.28 + uTime * 0.45) * 0.42 +
      sin(pos.y * 0.21 - uTime * 0.33) * 0.34;

    // ...and a radial ripple centred on the pointer gives it something to
    // react to. Falls off with distance so the effect stays local.
    float d = distance(pos.xy, uPointer);
    float ripple = sin(d * 1.5 - uTime * 2.6) * exp(-d * 0.28);

    // Scroll energy amplifies the ripple, so flicking down the page visibly
    // disturbs the floor instead of the scene feeling inert.
    float amount = mix(1.0, 0.25, uReduced);
    float elevation = (swell + ripple * (0.55 + uEnergy * 2.2)) * amount;

    pos.z += elevation;

    vElevation = elevation;
    vRipple = ripple;

    vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
    gl_Position = projectionMatrix * mvPosition;
    gl_PointSize = uSize * (1.0 + elevation * 0.55) * (18.0 / -mvPosition.z);
  }
`;

const GRID_FRAG = /* glsl */ `
  uniform vec3 uColorLow;
  uniform vec3 uColorHigh;

  varying float vElevation;
  varying float vRipple;

  void main() {
    // Round the square gl_Point into a soft dot.
    vec2 uv = gl_PointCoord - 0.5;
    float dist = length(uv);
    if (dist > 0.5) discard;
    float falloff = smoothstep(0.5, 0.05, dist);

    float lift = clamp(vElevation * 0.6 + 0.5, 0.0, 1.0);
    vec3 color = mix(uColorLow, uColorHigh, lift);

    // Crests of the pointer ripple flare brighter than the ambient swell.
    float flare = clamp(abs(vRipple) * 1.8, 0.0, 1.0);
    float alpha = falloff * (0.07 + lift * 0.26 + flare * 0.3);

    gl_FragColor = vec4(color, alpha);
  }
`;

export function createGridMaterial() {
  return new THREE.ShaderMaterial({
    vertexShader: GRID_VERT,
    fragmentShader: GRID_FRAG,
    uniforms: {
      uTime: { value: 0 },
      uPointer: { value: new THREE.Vector2(0, 0) },
      uEnergy: { value: 0 },
      uSize: { value: 2.2 },
      uReduced: { value: 0 },
      uColorLow: { value: new THREE.Color("#12304a") },
      uColorHigh: { value: new THREE.Color("#00f0ff") },
    },
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
}
