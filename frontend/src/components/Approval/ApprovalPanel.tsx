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
  const decisionSummary = getDecisionSummary(incident);
  const hasChatTranscript = events.some(
    (event) =>
      event.action === "operator_question" ||
      event.action === "agent_response" ||
      event.action === "more_info",
  );
  const isPending =
    incident.status === "pending_approval" ||
    incident.status === "escalated";
  const isAwaitingAgents = incident.status === "awaiting_agents";
  const shouldShowChat = isPending || isAwaitingAgents || hasChatTranscript;

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
      : decisionSummary?.title ?? "Operator review complete";
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

      {decisionSummary && !isPending && !isAwaitingAgents && (
        <div className={`approval-summary approval-summary--primary approval-summary--${decisionSummary.tone}`}>
          <div className="approval-summary-block">
            <span className="approval-summary-label">Decision outcome</span>
            <p className="approval-summary-value approval-summary-value--primary">
              {decisionSummary.lead}
            </p>
          </div>

          {(decisionSummary.detail || decisionSummary.secondaryDetail || decisionSummary.actor) && (
            <div className="approval-summary-columns">
              {decisionSummary.detail && (
                <div className="approval-summary-block">
                  <span className="approval-summary-label">{decisionSummary.detailLabel}</span>
                  <p className="approval-summary-value">{decisionSummary.detail}</p>
                </div>
              )}

              {decisionSummary.secondaryDetail && decisionSummary.secondaryDetailLabel && (
                <div className="approval-summary-block approval-summary-block--compact">
                  <span className="approval-summary-label">{decisionSummary.secondaryDetailLabel}</span>
                  <p className="approval-summary-value">{decisionSummary.secondaryDetail}</p>
                </div>
              )}

              {decisionSummary.actor && (
                <div className="approval-summary-block approval-summary-block--compact">
                  <span className="approval-summary-label">Recorded by</span>
                  <p className="approval-summary-value approval-summary-value--stacked">
                    {decisionSummary.actor.identifier && (
                      <span className="approval-summary-actor-id">{decisionSummary.actor.identifier}</span>
                    )}
                    {decisionSummary.actor.role && (
                      <span className="approval-summary-actor-role">{decisionSummary.actor.role}</span>
                    )}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

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

      {shouldShowChat && (
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
      )}

      {showRejectModal && (
        <RejectModal
          onConfirm={handleReject}
          onCancel={() => setShowRejectModal(false)}
        />
      )}
    </div>
  );
}

type DecisionSummaryTone = "approved" | "rejected" | "info";

interface DecisionSummary {
  title: string;
  lead: string;
  detailLabel: string;
  detail?: string;
  actor?: DecisionActor;
  tone: DecisionSummaryTone;
  secondaryDetailLabel?: string;
  secondaryDetail?: string;
}

interface DecisionActor {
  identifier?: string;
  role?: string;
}

function getDecisionSummary(incident: Incident): DecisionSummary | null {
  const finalDecision = incident.finalDecision?.action ? incident.finalDecision : undefined;
  const lastDecision = incident.lastDecision?.action ? incident.lastDecision : undefined;
  const decision = finalDecision ?? lastDecision;
  const rejectedDecision = [finalDecision, lastDecision].find(
    (item) => String(item?.action || "").trim().toLowerCase() === "rejected",
  );
  const operatorRejectComment = rejectedDecision?.reason?.trim();
  const closureReason = incident.rejectionReason?.trim();
  const action = incident.status === "rejected"
    ? "rejected"
    : String(decision?.action || (closureReason ? "rejected" : "")).trim().toLowerCase();
  const actor = formatDecisionActor(decision?.user_id, decision?.role);

  if (action === "rejected") {
    const detail = operatorRejectComment || closureReason || "No explicit rejection comment was recorded.";
    const secondaryDetail = operatorRejectComment && closureReason && closureReason !== operatorRejectComment
      ? closureReason
      : undefined;

    return {
      title: "Recommendation rejected",
      lead: operatorRejectComment
        ? "The operator rejected the AI recommendation and closed the incident without CAPA execution."
        : "The AI recommendation was rejected and the incident was closed without CAPA execution.",
      detailLabel: operatorRejectComment ? "Operator rejection comment" : "Closure reason",
      detail,
      actor: formatDecisionActor(rejectedDecision?.user_id, rejectedDecision?.role) ?? actor,
      tone: "rejected",
      secondaryDetailLabel: secondaryDetail ? "System closure note" : undefined,
      secondaryDetail,
    };
  }

  if (action === "approved") {
    return {
      title: "Recommendation approved",
      lead: "The recommendation was approved and moved forward for CAPA execution.",
      detailLabel: "Approval note",
      detail: decision?.reason,
      actor,
      tone: "approved",
    };
  }

  if (action === "more_info") {
    return {
      title: "More information requested",
      lead: "The operator requested a follow-up answer from the AI agent before deciding.",
      detailLabel: "Question asked",
      detail: decision?.question || decision?.reason,
      actor,
      tone: "info",
    };
  }

  return null;
}

function formatDecisionActor(userId?: string, role?: string): DecisionActor | undefined {
  const normalizedUserId = userId?.trim();
  const normalizedRole = role?.trim();

  if (!normalizedUserId && !normalizedRole) return undefined;
  return {
    identifier: normalizedUserId,
    role: normalizedRole,
  };
}
