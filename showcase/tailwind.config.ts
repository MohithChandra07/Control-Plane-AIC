import type { Config } from "tailwindcss";

/**
 * Showcase design system. Colour names mirror the governance vocabulary the
 * rest of the repo uses (ALLOW/MODIFY/ESCALATE/BLOCK) so the marketing site
 * and console/frontend stay visually consistent.
 */
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        void: "#05070c",
        abyss: "#080b13",
        glass: "rgba(15, 23, 42, 0.65)",
        cyber: {
          cyan: "#00f0ff",
          violet: "#8b5cf6",
          indigo: "#6366f1",
        },
        verdict: {
          allow: "#10b981",
          modify: "#3b82f6",
          escalate: "#f59e0b",
          block: "#ef4444",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      backdropBlur: {
        glass: "16px",
      },
      boxShadow: {
        neon: "0 0 0 1px rgba(0, 240, 255, 0.25), 0 0 32px -8px rgba(0, 240, 255, 0.45)",
        violet: "0 0 0 1px rgba(139, 92, 246, 0.3), 0 0 40px -10px rgba(139, 92, 246, 0.55)",
      },
      keyframes: {
        pulseDot: {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: "0.35", transform: "scale(0.72)" },
        },
        scanline: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100%)" },
        },
        floaty: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
      },
      animation: {
        "pulse-dot": "pulseDot 1.6s ease-in-out infinite",
        scanline: "scanline 6s linear infinite",
        floaty: "floaty 5s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
