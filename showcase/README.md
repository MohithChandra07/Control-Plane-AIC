# ControlPlane.ai — WebGL Showcase

A standalone Next.js (App Router) marketing/showcase site for ControlPlane:
a fixed full-viewport WebGL scene with GSAP-scrubbed camera choreography,
under a five-section DOM overlay (hero → adaptive scrutiny → taint engine →
live console → interactive gateway demo).

**This app is additive at build time.** It does not import from the
governance gateway (`gateway/`), the console API (`console/backend/`), or
the existing Vite + React console dashboard (`console/frontend/`) — its own
`package.json`, its own `node_modules`, its own build output, its own port.
`npm run build` succeeds with nothing else in the repository running.

**At runtime, `/console` optionally talks to the real backend — through a
same-origin proxy, never a direct cross-origin browser call.** The browser
only ever fetches relative paths like `/api/tenants` (see `lib/api.ts`).
Next's own server rewrites `/api/:path*` to `console/backend` server-to-
server (see the `rewrites()` in `next.config.mjs`, target configured by the
server-side `CONSOLE_BACKEND_URL` env var, default `http://127.0.0.1:8002`).
That's deliberate: a server-to-server proxy call is never subject to the
browser's CORS policy, so this can't fail as a cross-origin block no matter
what port the showcase or the backend run on. If the backend answers, every
number on the page — summary, decision distribution, the interaction table,
claim/tool-call inspection, risk appetite, human review, the tenant policy
cards — is a real query or write against the audit ledger, same as
`console/frontend`. If nothing answers within ~3s (the common case for a
standalone showcase deploy), it falls back to the deterministic demo data in
`components/console/mockData.ts`, and says so in a status banner at the top
of the page — never silently. See "Real data vs. showcase data" below.

| | `console/frontend` | `showcase` (`/console`) |
| --- | --- | --- |
| Purpose | Operating the gateway — live audit ledger, drill-downs, admin writes | Same operations, presented in the showcase's visual language |
| Stack | Vite + React 18, hand-written CSS | Next.js 14 App Router, plain CSS (`.cp-*` classes in `globals.css`) |
| Data | Live, from `console/backend` on `:8002` by default | Live from the same API when reachable, else labeled demo data |
| Dev port | 5173 | 3000 |

## Real data vs. showcase data

- **Landing page** (`/`): entirely static/deterministic — telemetry from
  `lib/telemetry.ts` (sourced from committed `bench/results/*.json`), and
  the Interactive Gateway Demo (`components/sections/GatewayDemo.tsx`,
  data in `lib/demoScenarios.ts`) is a precomputed walkthrough, not a live
  model call — each stage cites the real `configs/*.yaml` field driving it,
  but it doesn't hit the gateway. Wiring it to a live request means a POST
  to the gateway's `/v1/chat/completions` with an `X-ControlPlane-Tenant`
  header — see `gateway/routes/chat.py`.
- **Console** (`/console`): live when `console/backend` is reachable
  (see above), demo data (clearly labeled, from `mockData.ts`) otherwise.
  The one exception is the Policy Engine tab: `configs/*.yaml` doesn't
  change at runtime, so its fallback (`FALLBACK_POLICIES` in
  `ConsoleApp.tsx`) is a byte-for-byte transcription of the same three YAML
  files `policy/loader.py` reads, not invented data.
- **Request Demo** form: a UI placeholder, honestly labeled as such on
  submit — it isn't wired to a CRM or mail provider, so nothing is actually
  sent anywhere yet.

## Running it

```bash
cd showcase
npm install
npm run dev        # http://localhost:3000
```

```bash
npm run build && npm run start   # production
npm run typecheck                # tsc --noEmit
```

Both apps can run at the same time — different ports, different dependency
trees. Neither needs the other to be running.

### Running the console against live data

```bash
# from the repo root
python -m demo.replayer.replay --count 10000
DATABASE_URL="sqlite+aiosqlite:///$(pwd)/demo/replayer/traffic.db" \
  uvicorn console.backend.main:app --port 8002

# in showcase/
npm run dev   # or build && start
```

Open `http://localhost:3000/console` — the status banner at the top switches
from "no console/backend reachable" to "connected", and every panel (Policy
Engine included) switches to live ledger data.

The backend's default is `127.0.0.1:8002` (`next.config.mjs`'s
`CONSOLE_BACKEND_URL` default) — if it runs somewhere else, override the
**server-side** `CONSOLE_BACKEND_URL` env var, which configures the Next.js
rewrite destination and is never sent to the browser:

```bash
CONSOLE_BACKEND_URL=http://127.0.0.1:8002 npm run dev -- -p 3001
```

**This must be set before the command that actually starts the persistent
server, and for a production build that's `next build`, not `next start`.**
Next.js resolves a rewrite's destination once, when `next.config.mjs` loads
— for `next dev` that's every time the dev server (re)starts, but for a
production build it happens during `next build` and gets baked into the
build output; setting the env var only before `npm run start` has no
effect (verified: with `CONSOLE_BACKEND_URL` set solely at `next start`
time, requests still went to whatever was set at build time). So for
production, build with the target's real address:

```bash
CONSOLE_BACKEND_URL=http://127.0.0.1:8002 npm run build
npm run start -- -p 3001
```

`console/backend`'s `CONSOLE_CORS_ORIGINS` setting doesn't matter for the
showcase any more — a same-origin `/api/*` request proxied server-to-server
never goes through the browser's CORS check at all, regardless of which
port the showcase runs on. It's still relevant for `console/frontend`,
which does call the backend directly from the browser.

## Where the numbers come from

Every figure on the page lives in `lib/telemetry.ts`, and each one carries a
`source` string naming the artefact it was read from. The UI surfaces that
source in a `title` tooltip or a footnote, so a reader can go check it.

- `bench/results/benchmark_results.json` — written by
  `python -m bench.harness.run_benchmark` (seed 42, 400 labelled interactions).
  Source of the Tier 0 p50, the adaptive p50/p95, the tier-1 invocation rate,
  hallucination/PII recall, and the 0.160 ECE.
- `bench/results/appetite_sweep_results.json` — written by
  `python -m bench.harness.run_appetite_sweep`. Source of the risk-appetite
  sweep chart.
- The "150 tests passing" pill — `pytest -q` at the repo root.

Nothing here is invented for the visual, and the unflattering rows are shown
too: `ALWAYS_SHALLOW` is on the page with its 0% recall, because that row is
the reason adaptive scrutiny exists (repo rule: never fabricate numbers, and
never quote only the flattering configuration).

Copy describing behaviour is drawn from what the gateway actually implements —
`gateway/routes/chat.py`, `policy/tool_gate.py`, `ledger/taint.py`,
`detectors/injection.py` — and from the scenes in `docs/demo-scenarios.md`.

## Structure

```
app/
  layout.tsx           Fonts (via <link>, not next/font — see globals.css), metadata
  page.tsx             Layer stack: canvas → veils → HUD → sections
  globals.css          Tailwind entry + design tokens
components/
  canvas/
    Scene.tsx          <Canvas>, WebGL capability check, window pointer tracking
    CameraRig.tsx      One GSAP timeline, scrubbed, driving a camera proxy
    GovernanceNode.tsx Icosahedron + torus knot, counter-rotating wireframe
    PillarRings.tsx    Five shield rings, one per responsibility pillar
    GridFloor.tsx      Point grid, vertex-displaced by pointer + scroll energy
    Hotspots.tsx       drei <Html> spatial markers, hero only
    Effects.tsx        Bloom / ChromaticAberration / Noise / Vignette
    materials.ts       The two hand-written GLSL materials
  hud/                 Fixed top nav and the vertical section rail
  providers/           Lenis inertia scroll; the one place scroll state enters
  sections/            The five DOM sections (incl. GatewayDemo.tsx)
  ui/                  GlassCard, Reveal, RequestDemoModal, small primitives
  console/
    ConsoleApp.tsx     /console — live-or-demo governance console (see below)
    mockData.ts        Deterministic fallback data, used only when
                        console/backend isn't reachable
lib/
  telemetry.ts         Every number on the landing page, with its source
  demoScenarios.ts     Interactive Gateway Demo walkthroughs, each stage
                        citing the real configs/*.yaml field behind it
  api.ts               Typed fetch client — relative /api/* paths only,
                        proxied to console/backend by next.config.mjs
  viewport-store.ts    Mutable singleton shared by GSAP and the render loop
```

### Two notes on how it is wired

**Scroll and pointer state are not React state.** They update every frame;
routing them through `setState` would re-render the overlay 60+ times a
second. `lib/viewport-store.ts` is a plain mutable object that GSAP and Lenis
write into and `useFrame` reads from. React re-renders only when the
*discrete* active section changes.

**`pointer-events` is load-bearing.** The canvas sits at `z-0` with pointer
events enabled so the 3D hotspots stay clickable; `<main>` and each section
are `pointer-events: none`, and the copy columns, cards and buttons opt back
in individually. Making `<main>` interactive would silently swallow every
event before the canvas saw it.

## Accessibility and degradation

- No WebGL: `Scene` detects it and renders a static gradient instead. All
  copy and telemetry live in the DOM overlay, so the page stays complete.
- `prefers-reduced-motion`: Lenis smooth-wheel is disabled, entrance
  animations snap to their final state, and the scene's rotation, float and
  grid displacement are damped down.
- The canvas wrapper is deliberately **not** `aria-hidden` — the hotspot
  markers inside it are real buttons with text, and hiding the subtree would
  take them away from assistive tech.
- The page is server-rendered apart from the canvas, so the content is in the
  initial HTML.

## Verified in this repo

- `npm run build` — compiles clean, 3 static routes (`/`, `/console`, 404).
- `npx tsc --noEmit` — clean under `strict`.
- Rendered in headless Chromium at 1440×900: landing page loads with the
  five-section rail, the Interactive Gateway Demo switches decisions per
  tenant scenario, and the Request Demo modal opens.
- `/console` rendered against a real backend (`console/backend` on `:8002`
  over a SQLite ledger populated by `demo.replayer`): status banner reports
  "connected", the Overview/Interactions/Policy Engine/Human Review tabs all
  show live data, and clicking a row opens the drawer with real claims and
  tool-call evidence from the audit ledger.
