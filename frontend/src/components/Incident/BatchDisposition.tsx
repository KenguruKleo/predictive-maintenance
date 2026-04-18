import type { AiAnalysis } from "../../types/incident";
import { labelize } from "../../utils/analysis";

const DISPOSITION_CONFIG: Record<
  string,
  { tone: string; label: string }
> = {
  in_production: { tone: "approved", label: "In Production" },
  hold: { tone: "rejected", label: "Hold" },
  conditional_release: { tone: "warning", label: "Conditional Release" },
  conditional_release_pending_testing: { tone: "warning", label: "Conditional Release Pending Testing" },
  released: { tone: "approved", label: "Released" },
  rejected: { tone: "neutral", label: "Rejected" },
  pending: { tone: "warning", label: "Pending" },
  quarantine: { tone: "rejected", label: "Quarantine" },
  under_review: { tone: "warning", label: "Under Review" },
};

interface Props {
  batchId?: string;
  product?: string;
  analysis?: AiAnalysis;
}

export default function BatchDisposition({ batchId, product, analysis }: Props) {
  if (!batchId || !analysis?.batch_disposition) return null;

  const recommended =
    DISPOSITION_CONFIG[analysis.batch_disposition] ??
    { tone: "neutral", label: labelize(analysis.batch_disposition) };

  return (
    <section className="incident-section">
      <h3 className="section-title">Batch Release Recommendation</h3>
      <p className="muted-text disposition-summary-text">
        This is the AI recommendation for how the batch should proceed once the deviation is reviewed.
      </p>
      <dl className="info-grid">
        <dt>Batch</dt>
        <dd>{batchId}</dd>
        {product && (
          <>
            <dt>Product</dt>
            <dd>{product}</dd>
          </>
        )}
      </dl>
      <div className="disposition-recommendation">
        <strong>Recommended outcome:</strong>
        <span className={`disposition-indicator disposition-indicator--${recommended.tone}`}>
          {recommended.label}
        </span>
      </div>
      {analysis.disposition_conditions &&
        analysis.disposition_conditions.length > 0 && (
          <div className="disposition-conditions">
            <strong>Conditions:</strong>
            <ul>
              {analysis.disposition_conditions.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          </div>
        )}
    </section>
  );
}
