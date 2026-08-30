"use client";

import { cn } from "@/lib/utils";

/**
 * The one glass surface every panel on the site is built from. Centralised so
 * blur radius, border alpha and the hover glow stay identical everywhere —
 * inconsistent glass is what makes this aesthetic look cheap.
 */
export function GlassCard({
  className,
  children,
  accent,
  interactive = true,
  ...rest
}: React.HTMLAttributes<HTMLDivElement> & { accent?: string; interactive?: boolean }) {
  return (
    <div
      {...rest}
      className={cn(
        "pointer-events-auto relative overflow-hidden rounded-xl border border-white/[0.09]",
        "bg-[#121927]",
        "transition-[border-color,box-shadow,transform] duration-300",
        interactive && "hover:-translate-y-0.5 hover:border-white/[0.16]",
        className
      )}
      style={
        accent
          ? ({ "--accent": accent } as React.CSSProperties & Record<string, string>)
          : undefined
      }
    >
      {children}
    </div>
  );
}

export function SectionLabel({ index, children }: { index: string; children: React.ReactNode }) {
  return (
    <p className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-[0.3em] text-white/40">
      <span className="text-cyber-cyan">{index}</span>
      <span className="h-px w-8 bg-gradient-to-r from-cyber-cyan/60 to-transparent" />
      {children}
    </p>
  );
}

export function Stat({
  value,
  unit,
  label,
  source,
  accent = "#00f0ff",
}: {
  value: string;
  unit?: string;
  label: string;
  source?: string;
  accent?: string;
}) {
  return (
    <div className="min-w-0" title={source ? `Source: ${source}` : undefined}>
      <p className="font-mono text-2xl font-semibold tabular-nums" style={{ color: accent }}>
        {value}
        {unit ? <span className="ml-0.5 text-sm text-white/40">{unit}</span> : null}
      </p>
      <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.16em] text-white/40">{label}</p>
    </div>
  );
}
