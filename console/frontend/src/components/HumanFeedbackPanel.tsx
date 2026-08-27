import { useEffect, useState } from "react";
import { api } from "../api";
import type { HumanAgreement, Recalibration } from "../types";

export function HumanFeedbackPanel({ tenant, refreshKey }: { tenant: string; refreshKey: number }) {
  const [agreement, setAgreement] = useState<HumanAgreement | null>(null);
  const [recalibration, setRecalibration] = useState<Recalibration | null>(null);

  useEffect(() => {
    api.humanAgreement(tenant).then(setAgreement).catch(() => setAgreement(null));
    api.recalibration(tenant).then(setRecalibration).catch(() => setRecalibration(null));
  }, [tenant, refreshKey]);

  if (!agreement) return null;

  return (
    <div className="panel">
      <h2>Human review — {tenant}</h2>
      {agreement.reviewed_count === 0 ? (
        <div className="empty">
          No reviews yet. Open a request below and vote Agree/Disagree on its decision to start
          building a feedback loop.
        </div>
      ) : (
        <>
          <p style={{ fontSize: 13 }}>
            <strong>{(agreement.agreement_rate! * 100).toFixed(0)}%</strong> agreement across{" "}
            <strong>{agreement.reviewed_count}</strong> reviewed decisions.
          </p>
          {recalibration?.suggestion && (
            <div className="suggestion-banner">
              <strong>Recalibration suggestion:</strong> {recalibration.suggestion.message}
            </div>
          )}
        </>
      )}
    </div>
  );
}
