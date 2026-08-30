"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, TriangleAlert, X } from "lucide-react";
import { GlassCard } from "./Glass";
import { submitDemoRequest, type DemoRequestPayload } from "@/lib/api";

const CONCERNS = ["Performance", "Cost", "Privacy", "Safety", "Governance", "AI Agents"] as const;

export function RequestDemoModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Clears a stale error each time the modal is reopened; a prior
  // successful submission is left alone so reopening doesn't invite a
  // second one.
  useEffect(() => {
    if (open) setError(null);
  }, [open]);

  if (!open) return null;

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (submitting) return; // belt-and-braces against a double Enter/click

    const data = new FormData(e.currentTarget);
    const payload: DemoRequestPayload = {
      name: String(data.get("name") ?? "").trim(),
      work_email: String(data.get("email") ?? "").trim(),
      company: String(data.get("company") ?? "").trim(),
      role: String(data.get("role") ?? "").trim(),
      ai_use_case: String(data.get("useCase") ?? "").trim(),
      primary_concern: String(data.get("concern") ?? "").trim(),
    };

    if (!payload.name || !payload.work_email || !payload.company || !payload.primary_concern) {
      setError("Please fill in your name, work email, company, and primary concern.");
      return;
    }

    setError(null);
    setSubmitting(true);
    try {
      await submitDemoRequest(payload);
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="pointer-events-auto fixed inset-0 z-[70] flex items-center justify-center bg-black/70 px-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <GlassCard
        className="max-h-[85vh] w-full max-w-md overflow-y-auto p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-cyber-cyan">Request a demo</p>
            <h3 className="mt-1.5 text-lg font-semibold text-white">Talk to us about ControlPlane</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-white/[0.08] text-white/50 hover:text-white"
          >
            <X size={15} />
          </button>
        </div>

        {submitted ? (
          <div className="mt-8 flex flex-col items-center gap-3 py-6 text-center">
            <CheckCircle2 size={28} className="text-verdict-allow" aria-hidden />
            <p className="text-[14px] font-medium text-white/85">Request received.</p>
            <p className="max-w-xs text-[12.5px] leading-relaxed text-white/50">
              Thanks for your interest in ControlPlane. We&apos;ve received your request and will
              reach out to you at the earliest.
            </p>
            <button
              type="button"
              onClick={onClose}
              className="mt-2 rounded-lg border border-white/[0.14] px-4 py-2 font-mono text-[11px] uppercase tracking-[0.16em] text-white/70 hover:border-white/[0.24] hover:text-white"
            >
              Close
            </button>
          </div>
        ) : (
          <form className="mt-6 space-y-3.5" onSubmit={handleSubmit}>
            <Field label="Name" name="name" required disabled={submitting} />
            <Field label="Work email" name="email" type="email" required disabled={submitting} />
            <Field label="Company" name="company" required disabled={submitting} />
            <Field label="Role" name="role" disabled={submitting} />
            <Field label="AI use case" name="useCase" textarea disabled={submitting} />

            <div>
              <label className="font-mono text-[10px] uppercase tracking-[0.16em] text-white/45">
                Primary concern
              </label>
              <select
                name="concern"
                required
                disabled={submitting}
                className="mt-1.5 w-full rounded-lg border border-white/[0.12] bg-[#0b1018] px-3 py-2.5 text-[13px] text-white/85 outline-none focus:border-cyber-cyan/40 disabled:opacity-50"
                defaultValue=""
              >
                <option value="" disabled>
                  Select a concern
                </option>
                {CONCERNS.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            {error && (
              <div className="flex items-start gap-2 rounded-lg border border-verdict-block/30 bg-verdict-block/[0.08] px-3 py-2.5 text-[12px] leading-snug text-verdict-block/90">
                <TriangleAlert size={13} className="mt-0.5 shrink-0" aria-hidden />
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl border border-cyber-cyan/30 bg-cyber-cyan/[0.08] px-5 py-3 font-mono text-[11px] uppercase tracking-[0.18em] text-cyber-cyan transition-colors hover:bg-cyber-cyan/[0.15] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting && <Loader2 size={13} className="animate-spin" aria-hidden />}
              {submitting ? "Submitting…" : "Submit request"}
            </button>
          </form>
        )}
      </GlassCard>
    </div>
  );
}

function Field({
  label,
  name,
  type = "text",
  required,
  textarea,
  disabled,
}: {
  label: string;
  name: string;
  type?: string;
  required?: boolean;
  textarea?: boolean;
  disabled?: boolean;
}) {
  const className =
    "mt-1.5 w-full rounded-lg border border-white/[0.12] bg-[#0b1018] px-3 py-2.5 text-[13px] text-white/85 outline-none focus:border-cyber-cyan/40 disabled:opacity-50";
  return (
    <div>
      <label className="font-mono text-[10px] uppercase tracking-[0.16em] text-white/45">
        {label}
        {required ? " *" : ""}
      </label>
      {textarea ? (
        <textarea name={name} rows={3} disabled={disabled} className={className} />
      ) : (
        <input name={name} type={type} required={required} disabled={disabled} className={className} />
      )}
    </div>
  );
}
