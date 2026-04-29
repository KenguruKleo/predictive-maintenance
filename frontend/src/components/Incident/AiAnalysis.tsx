import type { AiAnalysis as AnalysisData } from "../../types/incident";
import {
  getCapaActions,
  getClassification,
  getConfidencePct,
  getRecommendation,
  getRootCause,
  isLowConfidenceAnalysis,
  labelize,
} from "../../utils/analysis";

const RISK_CONFIG: Record<string, { icon: string; className: string }> = {
  CRITICAL: { icon: "●", className: "risk--high" },
  HIGH: { icon: "🔴", className: "risk--high" },
  MEDIUM: { icon: "🟠", className: "risk--medium" },
  LOW: { icon: "🟢", className: "risk--low" },
  LOW_CONFIDENCE: { icon: "⚠️", className: "risk--low-confidence" },
};

interface Props {
  analysis: AnalysisData;
}

export default function AiAnalysis({ analysis }: Props) {
  const normalizedRisk = (isLowConfidenceAnalysis(analysis)
    ? "LOW_CONFIDENCE"
    : (analysis.risk_level ?? "").toUpperCase()) as keyof typeof RISK_CONFIG;
  const risk = RISK_CONFIG[normalizedRisk] ?? { icon: "ℹ️", className: "risk--low" };
  const confPct = getConfidencePct(analysis);
  const classification = getClassification(analysis);
  const rootCause = getRootCause(analysis);
  const recommendation = getRecommendation(analysis);
  const capaActions = getCapaActions(analysis);

  return (
    <section className="incident-section">
      <h3 className="section-title">AI Analysis</h3>

      <div className="analysis-row">
        <span className={`risk-badge ${risk.className}`}>
          {risk.icon} Risk: {normalizedRisk.replace("_", " ") || "Unknown"}
        </span>
        <span className="confidence-bar-wrap">
          Confidence:
          <span className="confidence-bar">
            <span
              className="confidence-fill"
              style={{ width: `${confPct}%` }}
            />
          </span>
          {confPct}%
        </span>
      </div>

      {classification && (
        <div className="analysis-field">
          <strong>Classification:</strong> {labelize(classification)}
        </div>
      )}
      {rootCause && (
        <div className="analysis-field">
          <strong>Root Cause:</strong> {rootCause}
        </div>
      )}
      {recommendation && (
        <div className="analysis-field">
          <strong>Recommendation:</strong> {recommendation}
        </div>
      )}

      {capaActions.length > 0 && (
        <div className="analysis-capa">
          <strong>CAPA Actions:</strong>
          <ol className="capa-list">
            {capaActions.map((action, i) => (
              <li key={i}>{action}</li>
            ))}
          </ol>
        </div>
      )}
    </section>
  );
}
