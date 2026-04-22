interface Props {
  agentRecommendation?: "APPROVE" | "REJECT";
  operatorAgreesWithAgent?: boolean | null;
}

export default function AiVsHumanBadge({ agentRecommendation, operatorAgreesWithAgent }: Props) {
  if (!agentRecommendation) return null;

  const agreed = operatorAgreesWithAgent === true;
  const pending = operatorAgreesWithAgent == null;

  return (
    <span
      className={`ai-vs-human-badge ai-vs-human-badge--${pending ? "pending" : agreed ? "agreed" : "override"}`}
      title={
        pending
          ? `AI recommended ${agentRecommendation} — awaiting operator decision`
          : agreed
          ? `AI recommended ${agentRecommendation} — operator agreed`
          : `AI recommended ${agentRecommendation} — operator overrode`
      }
    >
      {pending ? `AI: ${agentRecommendation}` : agreed ? `✓ Agreed` : `⚡ Override`}
    </span>
  );
}
