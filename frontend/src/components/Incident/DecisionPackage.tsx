import type { Incident } from "../../types/incident";
import {
  getAllCitations,
  getCapaActions,
  getClassification,
  getConfidencePct,
  getParameterSummary,
  getRecommendation,
  getRootCause,
  labelize,
} from "../../utils/analysis";
import EvidenceCitations from "./EvidenceCitations";

interface Props {
  incident: Incident;
}

export default function DecisionPackage({ incident }: Props) {
  const analysis = incident.ai_analysis;
  const parameter = getParameterSummary(incident);
  const citations = getAllCitations(analysis);
  const capaActions = getCapaActions(analysis);

  return (
    <section className="decision-package">
      <h2 className="decision-package-title">Decision Package</h2>

      <div className="decision-summary-strip">
        <div className="decision-summary-strip-header">
          <h3 className="section-title">Incident Summary</h3>
          <span className="decision-summary-strip-text">
            What happened and where it affects the batch.
          </span>
        </div>
        <div className="decision-metric-grid">
          <Metric label="Equipment" value={incident.equipment_id} />
          <Metric label="Batch" value={incident.batch_id} />
          <Metric label="Product" value={incident.product} />
          <Metric label="Stage" value={incident.production_stage} />
          <Metric label="Parameter" value={parameter.parameter} />
          <Metric
            label="Measured"
            value={
              parameter.measuredValue !== undefined
                ? `${parameter.measuredValue} ${parameter.unit}`
                : undefined
            }
          />
          <Metric
            label="Limit"
            value={
              parameter.lowerLimit !== undefined && parameter.upperLimit !== undefined
                ? `${parameter.lowerLimit}-${parameter.upperLimit} ${parameter.unit}`
                : undefined
            }
          />
          <Metric
            label="Duration"
            value={
              parameter.durationSeconds !== undefined
                ? `${Math.floor(parameter.durationSeconds / 60)}m ${parameter.durationSeconds % 60}s`
                : undefined
            }
          />
          <Metric label="Severity" value={incident.severity} />
          <Metric label="Status" value={incident.status} />
        </div>
      </div>

      {analysis && (
        <div className="decision-section decision-section--primary">
          <h3 className="section-title">AI Recommendation</h3>
          <div className="decision-summary-grid">
            <Metric label="Risk" value={analysis.risk_level} />
            <Metric label="Confidence" value={`${getConfidencePct(analysis)}%`} />
            <Metric label="Classification" value={getClassification(analysis)} />
            <Metric label="Batch disposition" value={analysis.batch_disposition} />
          </div>
          {getRecommendation(analysis) && (
            <div className="decision-text-block decision-text-block--highlight">
              <strong>Recommended action</strong>
              <p>{getRecommendation(analysis)}</p>
            </div>
          )}
          {getRootCause(analysis) && (
            <div className="decision-text-block">
              <strong>Root cause</strong>
              <p>{getRootCause(analysis)}</p>
            </div>
          )}
        </div>
      )}

      {citations.length > 0 && (
        <div className="decision-section decision-section--supporting">
          <EvidenceCitations citations={citations} />
        </div>
      )}

      {analysis && (
        <div className="decision-section decision-section--supporting">
          <h3 className="section-title">After Approval</h3>
          {capaActions.length > 0 && (
            <div className="approval-outcome-block">
              <strong>CAPA actions</strong>
              <ol className="capa-list">
                {capaActions.map((action, i) => (
                  <li key={i}>{action}</li>
                ))}
              </ol>
            </div>
          )}
          <DraftBlock title="Work order draft" draft={analysis.work_order_draft} />
          <DraftBlock title="Audit entry draft" draft={analysis.audit_entry_draft} />
        </div>
      )}
    </section>
  );
}

function Metric({ label, value }: { label: string; value?: string | number }) {
  return (
    <div className="decision-metric">
      <span>{label}</span>
      <strong>{labelize(value)}</strong>
    </div>
  );
}

function DraftBlock({
  title,
  draft,
}: {
  title: string;
  draft?: Record<string, unknown>;
}) {
  if (!draft || Object.keys(draft).length === 0) return null;
  return (
    <div className="draft-block">
      <strong>{title}</strong>
      <dl className="draft-grid">
        {Object.entries(draft).map(([key, value]) => (
          <div key={key}>
            <dt>{labelize(key)}</dt>
            <dd>{typeof value === "object" ? JSON.stringify(value) : labelize(String(value))}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
