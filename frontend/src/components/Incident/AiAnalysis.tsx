import type { AiAnalysis as AnalysisData } from "../../types/incident";

const RISK_CONFIG: Record<string, { icon: string; className: string }> = {
  HIGH: { icon: "🔴", className: "risk--high" },
  MEDIUM: { icon: "🟠", className: "risk--medium" },
  LOW: { icon: "🟢", className: "risk--low" },
  LOW_CONFIDENCE: { icon: "⚠️", className: "risk--low-confidence" },
};

interface Props {
  analysis: AnalysisData;
}

export default function AiAnalysis({ analysis }: Props) {
  // risk_level may come uppercase or lowercase from different sources
  const normalizedRisk = (analysis.risk_level ?? "").toUpperCase() as keyof typeof RISK_CONFIG;
  const risk = RISK_CONFIG[normalizedRisk] ?? { icon: "ℹ️", className: "risk--low" };
  const confidence = analysis.confidence ?? 0;
  const confPct = Math.round(confidence * (confidence <= 1 ? 100 : 1));

  // capa_steps may be missing; fall back to capa_suggestion string
  const capaSteps: { step: number; description: string }[] =
    Array.isArray(analysis.capa_steps) && analysis.capa_steps.length > 0
      ? analysis.capa_steps
      : (analysis as any).capa_suggestion
        ? String((analysis as any).capa_suggestion)
            .split(/\n|\d+\.\s/)
            .map((s) => s.trim())
            .filter(Boolean)
            .map((description, i) => ({ step: i + 1, description }))
        : [];

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

      {((analysis as any).classification || analysis.deviation_classification) && (
        <div className="analysis-field">
          <strong>Classification:</strong>{" "}
          {analysis.deviation_classification ?? (analysis as any).classification}
        </div>
      )}
      {((analysis as any).root_cause_hypothesis || (analysis as any).recommendation) && (
        <div className="analysis-field">
          <strong>Root Cause:</strong>{" "}
          {(analysis as any).root_cause_hypothesis ?? (analysis as any).recommendation}
        </div>
      )}

      {capaSteps.length > 0 && (
        <div className="analysis-capa">
          <strong>CAPA Steps:</strong>
          <ol className="capa-list">
            {capaSteps.map((step, i) => (
              <li key={step.step ?? i}>{step.description}</li>
            ))}
          </ol>
        </div>
      )}
    </section>
  );
}
