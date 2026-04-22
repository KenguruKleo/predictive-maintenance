interface Props {
  recommendation: "APPROVE" | "REJECT";
  overridden?: boolean;
}

export default function AgentRecommendationBadge({ recommendation, overridden }: Props) {
  const isApprove = recommendation === "APPROVE";
  const colorClass = overridden ? "overridden" : isApprove ? "approve" : "reject";
  return (
    <div className={`agent-rec-badge agent-rec-badge--${colorClass}`}>
      <span className="agent-rec-badge-icon">AI</span>
      <div className="agent-rec-badge-body">
        <span className="agent-rec-badge-label">
          {overridden ? "AI recommendation (operator overrode)" : "AI recommendation"}
        </span>
        <strong className="agent-rec-badge-verdict">
          {isApprove
            ? "✓ APPROVE — incident confirmed, action required"
            : "✕ REJECT — transient / no action required"}
        </strong>
      </div>
    </div>
  );
}
