import { cn } from "@/lib/utils";

/**
 * Shell for each scroll section.
 *
 * pointer-events:none is the load-bearing detail — the WebGL canvas sits
 * underneath at z-0 and must keep receiving pointer events for the 3D hotspots
 * and the grid ripple. Anything the user is meant to click re-enables them
 * locally (GlassCard and the HUD buttons already do).
 */
export function Section({
  id,
  index,
  className,
  children,
}: {
  id: string;
  index: number;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <section
      id={id}
      data-section-index={index}
      className={cn(
        "pointer-events-none relative z-10 flex min-h-screen w-full items-center",
        "px-5 pb-24 pt-40 sm:px-8 sm:pt-36 lg:px-16 lg:py-28 xl:pl-56",
        className
      )}
    >
      <div className="mx-auto w-full max-w-[1400px]">{children}</div>
    </section>
  );
}
