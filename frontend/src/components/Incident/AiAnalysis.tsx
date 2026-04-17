import type { AiAnalysis as AnalysisData } from "../../types/incident";

const RISK_CONFIG = {
  HIGH: { icon: "🔴", className: "risk--high" },
  MEDIUM: { icon: "🟠", className: "risk--medium" },
  LOW: { icon: "🟢", className: "risk--low" },
  LOW_CONFIDENCE: { icon: "⚠️", className: "risk--low-confidence" },
};

interface Props {
  analysis: AnalysisData;
}

export default function AiAnalysis({ analysis }: Props) {
  const risk = RISK_CONFIG[analysis.risk_level];
  const confPct = Math.round(analysis.confidence * 100);

  return (
    <section className="incident-section">
      <h3 className="section-title">AI Analysis</h3>

      <div className="analysis-row">
        <span className={`risk-badge ${risk.className}`}>
          {risk.icon} Risk: {analysis.risk_level.replace("_", " ")}
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

      {analysis.deviation_classification && (
        <div className="analysis-field">
          <strong>Classification:</strong> {analysis.deviation_classification}
        </div>
      )}
      {analysis.root_cause_hypothesis && (
        <div className="analysis-field">
          <strong>Root Cause:</strong> {analysis.root_cause_hypothesis}
        </div>
      )}

      {analysis.capa_steps.length > 0 && (
        <div className="analysis-capa">
          <strong>CAPA Steps:</strong>
          <ol className="capa-list">
            {analysis.capa_steps.map((step) => (
              <li key={step.step}>{step.description}</li>
            ))}
          </ol>
        </div>
      )}
    </section>
  );
}
