import type { AiAnalysis } from "../../types/incident";

interface Props {
  analysis: AiAnalysis;
}

export default function ConfidenceBanner({ analysis }: Props) {
  if (analysis.risk_level !== "LOW_CONFIDENCE") return null;
  const pct = Math.round(analysis.confidence * 100);

  return (
    <div className="confidence-banner">
      <span className="confidence-banner-icon">⚠️</span>
      <div>
        <strong>LOW CONFIDENCE ({pct}%)</strong>
        <p>
          Insufficient evidence for a reliable recommendation. QA Manager review
          is recommended before proceeding.
        </p>
      </div>
    </div>
  );
}
