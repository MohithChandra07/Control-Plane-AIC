import type { Metadata } from "next";
import { ConsoleApp } from "@/components/console/ConsoleApp";

export const metadata: Metadata = { title: "ControlPlane.ai — Governance Console", description: "Operational AI governance console for request inspection, risk appetite and human review." };

export default function ConsolePage() { return <ConsoleApp />; }
