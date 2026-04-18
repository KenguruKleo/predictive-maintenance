import { useState } from "react";
import type { Incident, IncidentEvent } from "../../types/incident";
import { useSubmitDecision } from "../../hooks/useIncidents";
import ConfidenceBanner from "./ConfidenceBanner";
import RejectModal from "./RejectModal";
import AgentChat from "./AgentChat";
import {
  getConfidencePct,
  getRecommendation,
  getRootCause,
  labelize,
} from "../../utils/analysis";

interface Props {
  incident: Incident;
  events: IncidentEvent[];
}

export default function ApprovalPanel({ incident, events }: Props) {
  const [showRejectModal, setShowRejectModal] = useState(false);
  const decision = useSubmitDecision(incident.id);
  const isPending =
    incident.status === "pending_approval" ||
    incident.status === "escalated";

  const handleApprove = () => {
    decision.mutate({ action: "approved" });
  };

  const handleReject = (reason: string) => {
    decision.mutate({ action: "rejected", reason });
    setShowRejectModal(false);
  };

  const handleAskAgent = (question: string) => {
    decision.mutate({ action: "more_info", question });
  };

  return (
    <div className="approval-panel">
      {incident.ai_analysis && (
        <ConfidenceBanner analysis={incident.ai_analysis} />
      )}

      {isPending && (
        <>
          <div className="approval-summary">
            <h3 className="section-title">⚠️ Your Decision Required</h3>
            {incident.ai_analysis && (
              <div className="approval-recommendation">
                <p>
                  <strong>AI Recommendation:</strong>{" "}
                  {getRecommendation(incident.ai_analysis)}
                </p>
                {getRootCause(incident.ai_analysis) && (
                  <p>
                    <strong>Root Cause:</strong>{" "}
                    {getRootCause(incident.ai_analysis)}
                  </p>
                )}
                <p>
                  Risk: {labelize(incident.ai_analysis.risk_level)} ·
                  Confidence: {getConfidencePct(incident.ai_analysis)}%
                </p>
              </div>
            )}

            {incident.ai_analysis?.batch_disposition && (
              <div className="approval-batch-note">
                Batch {incident.batch_id} to {labelize(incident.ai_analysis.batch_disposition)}
              </div>
            )}
          </div>

          <div className="decision-buttons">
            <button
              className="btn btn--approve"
              onClick={handleApprove}
              disabled={decision.isPending}
            >
              ✅ Approve
            </button>
            <button
              className="btn btn--reject"
              onClick={() => setShowRejectModal(true)}
              disabled={decision.isPending}
            >
              ❌ Reject
            </button>
          </div>

          <div className="approval-divider">— or ask the agent —</div>
        </>
      )}

      <AgentChat
        events={events}
        onSend={isPending ? handleAskAgent : undefined}
        readOnly={!isPending}
      />

      {showRejectModal && (
        <RejectModal
          onConfirm={handleReject}
          onCancel={() => setShowRejectModal(false)}
        />
      )}
    </div>
  );
}
