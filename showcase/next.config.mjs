// Server-side only — never exposed to the browser (not NEXT_PUBLIC_*).
// Where the real console/backend (console/backend/main.py) actually listens.
// Override with CONSOLE_BACKEND_URL for a different host/port.
//
// IMPORTANT: Next.js resolves rewrite destinations when the config loads,
// and for a production build that happens during `next build`, not
// `next start` — the built output bakes in whatever CONSOLE_BACKEND_URL
// was set to at build time. Setting it only before `next start` has no
// effect. In `next dev` this isn't an issue: restarting the dev server
// re-reads it. See showcase/README.md's "Running the console against
// live data" section.
const CONSOLE_BACKEND_URL = (process.env.CONSOLE_BACKEND_URL || "http://127.0.0.1:8002").replace(/\/$/, "");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // three ships untranspiled ESM examples; Next needs to compile them.
  transpilePackages: ["three"],
  // The browser only ever calls same-origin /api/* — Next's own server proxies
  // that, server-to-server, to console/backend. This is what actually fixes
  // the "no console/backend reachable" CORS failure: a server-to-server proxy
  // request isn't subject to the browser's CORS policy at all, so it works
  // regardless of console/backend's CORS_ORIGINS setting or which port the
  // showcase itself is served from. See lib/api.ts.
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${CONSOLE_BACKEND_URL}/api/:path*` },
    ];
  },
};

export default nextConfig;
