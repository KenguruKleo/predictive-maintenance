import { useEffect, useId, useRef, useState } from "react";
import type { Incident, IncidentEvent } from "../../types/incident";
import { useSubmitDecision } from "../../hooks/useIncidents";
import ConfidenceBanner from "./ConfidenceBanner";
import RejectModal from "./RejectModal";
import AgentChat from "./AgentChat";
import StatusBadge from "../IncidentList/StatusBadge";

interface Props {
  incident: Incident;
  events: IncidentEvent[];
}

export default function ApprovalPanel({ incident, events }: Props) {
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [showQuestionComposer, setShowQuestionComposer] = useState(false);
  const decision = useSubmitDecision(incident.id);
  const chatInputId = useId();
  const chatInputRef = useRef<HTMLTextAreaElement>(null);
  const isPending =
    incident.status === "pending_approval" ||
    incident.status === "escalated";
  const isAwaitingAgents = incident.status === "awaiting_agents";

  useEffect(() => {
    if (!isPending) {
      setShowQuestionComposer(false);
      return;
    }

    if (showQuestionComposer) {
      requestAnimationFrame(() => {
        chatInputRef.current?.focus();
      });
    }
  }, [isPending, showQuestionComposer]);


  const handleApprove = () => {
    decision.mutate({ action: "approved" });
  };

  const handleReject = (reason: string) => {
    decision.mutate({ action: "rejected", reason });
    setShowRejectModal(false);
  };

  const handleAskAgent = (question: string) => {
    decision.mutate(
      { action: "more_info", question },
      {
        onSuccess: () => {
          setShowQuestionComposer(false);
        },
      },
    );
  };

  const handleNeedMoreInfo = () => {
    setShowQuestionComposer(true);
  };

  const panelTitle = isPending
    ? "Decision required"
    : isAwaitingAgents
      ? "Awaiting agent response"
      : "Operator review complete";
  const panelEyebrow = isPending
    ? "Decision required"
    : isAwaitingAgents
      ? "Question submitted"
      : "Decision summary";


  return (
    <div className="approval-panel approval-panel--sticky">
      <div className="approval-cockpit-header">
        <div>
          <p className="approval-eyebrow">{panelEyebrow}</p>
          <h2 className="approval-cockpit-title">{panelTitle}</h2>
        </div>
        <StatusBadge status={incident.status} />
      </div>

      {incident.ai_analysis && <ConfidenceBanner analysis={incident.ai_analysis} />}

      {isPending && (
        <>
          <div className="decision-buttons decision-buttons--triple">
            <button
              className="btn btn--approve"
              onClick={handleApprove}
              disabled={decision.isPending}
            >
              Approve
            </button>
            <button
              className="btn btn--reject"
              onClick={() => setShowRejectModal(true)}
              disabled={decision.isPending}
            >
              Reject
            </button>
            <button
              className="btn btn--secondary"
              onClick={handleNeedMoreInfo}
              disabled={decision.isPending}
              aria-controls={chatInputId}
            >
              Need More Info
            </button>
          </div>

          <div className="approval-divider">Ask the agent before deciding</div>
        </>
      )}

      <AgentChat
        events={events}
        onSend={isPending ? handleAskAgent : undefined}
        readOnly={!isPending}
        showComposer={isPending && showQuestionComposer}
        title="Conversation transcript"
        emptyState={
          isPending
            ? "Ask the AI agent for more details before deciding."
            : isAwaitingAgents
              ? "Waiting for the AI agent response to the latest operator question."
              : "No conversation has been recorded for this incident."
        }
        inputId={chatInputId}
        inputRef={chatInputRef}
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
