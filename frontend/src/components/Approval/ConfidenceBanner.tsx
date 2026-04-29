import type { AiAnalysis } from "../../types/incident";
import { isLowConfidenceAnalysis } from "../../utils/analysis";

interface Props {
  analysis: AiAnalysis;
}

export default function ConfidenceBanner({ analysis }: Props) {
  if (!isLowConfidenceAnalysis(analysis)) return null;
  const pct = Math.round(analysis.confidence * 100);

  return (
    <div className="confidence-banner confidence-banner--warning">
      <span className="confidence-banner-icon">Review</span>
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
