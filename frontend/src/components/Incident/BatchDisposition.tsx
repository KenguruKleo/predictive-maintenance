import type { AiAnalysis } from "../../types/incident";
import type { BatchDispositionStatus } from "../../types/incident";

const DISPOSITION_CONFIG: Record<
  BatchDispositionStatus,
  { icon: string; color: string; label: string }
> = {
  in_production: { icon: "🟢", color: "var(--color-approved)", label: "In Production" },
  hold: { icon: "🔴", color: "var(--color-rejected)", label: "Hold" },
  conditional_release: { icon: "🟡", color: "var(--color-escalated)", label: "Conditional Release" },
  released: { icon: "🟢", color: "var(--color-approved)", label: "Released" },
  rejected: { icon: "⚫", color: "var(--color-closed)", label: "Rejected" },
};

interface Props {
  batchId?: string;
  product?: string;
  analysis?: AiAnalysis;
}

export default function BatchDisposition({ batchId, product, analysis }: Props) {
  if (!batchId || !analysis?.batch_disposition) return null;

  const recommended = DISPOSITION_CONFIG[analysis.batch_disposition];

  return (
    <section className="incident-section">
      <h3 className="section-title">📦 Batch Disposition</h3>
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
        <strong>AI Recommendation:</strong>
        <span style={{ color: recommended.color }}>
          {recommended.icon} {recommended.label}
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
