import type { Metadata, Viewport } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "ControlPlane.ai — AI Governance & Safety Gateway",
  description:
    "ControlPlane sits between your application and the model: adaptive scrutiny, claim verification, multi-turn taint propagation and tool-call gating, on a hash-chained audit ledger.",
  keywords: [
    "AI governance",
    "AI safety gateway",
    "hallucination detection",
    "prompt injection",
    "tool-call gating",
    "audit ledger",
  ],
  openGraph: {
    title: "ControlPlane.ai — AI Governance & Safety Gateway",
    description:
      "Policy decides, not the model. Adaptive scrutiny, taint propagation across turns, and a hash-chained audit ledger.",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#05070c",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
