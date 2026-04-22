import { useEffect, useId, useRef, useState } from "react";
import type { Incident, IncidentEvent } from "../../types/incident";
import type { AuditEntryDraft, WorkOrderDraft } from "../../types/approval";
import { useSubmitDecision } from "../../hooks/useIncidents";
import ConfidenceBanner from "./ConfidenceBanner";
import AgentRecommendationBadge from "./AgentRecommendationBadge";
import RejectModal from "./RejectModal";
import AgentChat from "./AgentChat";
import StatusBadge from "../IncidentList/StatusBadge";

interface Props {
  incident: Incident;
  events: IncidentEvent[];
  canMakeDecision: boolean;
  draftState?: { workOrder: WorkOrderDraft; auditEntry: AuditEntryDraft };
}

export default function ApprovalPanel({ incident, events, canMakeDecision, draftState }: Props) {
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

  // Derive whether the operator overrode the agent's recommendation
  const agentRec = incident.ai_analysis?.agent_recommendation;
  const lastAction = incident.lastDecision?.action;
  const agentWasOverridden =
    incident.operatorAgreesWithAgent === false ||
    (incident.operatorAgreesWithAgent == null &&
      agentRec != null &&
      lastAction != null &&
      ((lastAction === "rejected" && agentRec === "APPROVE") ||
        (lastAction === "approved" && agentRec === "REJECT")));

  // BLOCKED = AI provided no draft at all (both WO and AuditEntry title/description are empty)
  const aiHasDraft = !!(
    incident.ai_analysis?.work_order_draft || incident.ai_analysis?.audit_entry_draft
  );
  const isBlocked = !aiHasDraft;
  const draftsFilledEnough =
    !isBlocked ||
    !!(draftState?.workOrder.description && draftState?.auditEntry.description);
  const approveDisabled = decision.isPending || (isPending && isBlocked && !draftsFilledEnough);

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
    decision.mutate({
      action: "approved",
      agent_recommendation: incident.ai_analysis?.agent_recommendation,
      work_order_draft: draftState?.workOrder,
      audit_entry_draft: draftState?.auditEntry,
    });
  };

  const handleReject = (reason: string) => {
    decision.mutate({
      action: "rejected",
      reason,
      agent_recommendation: incident.ai_analysis?.agent_recommendation,
    });
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
      {incident.ai_analysis?.agent_recommendation && isPending && (
        <AgentRecommendationBadge recommendation={incident.ai_analysis.agent_recommendation} />
      )}
      {incident.ai_analysis?.agent_recommendation && !isPending && !isAwaitingAgents && agentWasOverridden && (
        <AgentRecommendationBadge recommendation={incident.ai_analysis.agent_recommendation} overridden />
      )}

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

      {isPending && canMakeDecision && (
        <>
          {isBlocked && !draftsFilledEnough && (
            <p className="approval-blocked-hint">
              AI was unable to generate a work order or audit entry. Fill in the forms in the Decision Package before approving.
            </p>
          )}
          <div className="decision-buttons decision-buttons--triple">
            <button
              className="btn btn--approve"
              onClick={handleApprove}
              disabled={approveDisabled}
            >
              Approve
            </button>
            <button
              className="btn btn--reject"
              onClick={() => setShowRejectModal(true)}
              disabled={decision.isPending}
            >
              Decline
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
          onSend={canMakeDecision && isPending ? handleAskAgent : undefined}
          readOnly={!canMakeDecision || !isPending}
          showComposer={canMakeDecision && isPending && showQuestionComposer}
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
  const agentRec = incident.ai_analysis?.agent_recommendation ?? incident.agentRecommendation;

  // Human-readable label for what the AI recommended about the incident
  function agentRecLabel(rec: string | undefined): string | undefined {
    if (rec === "APPROVE") return "APPROVE — incident confirmed, action recommended";
    if (rec === "REJECT") return "REJECT — transient / no action required";
    return undefined;
  }

  if (action === "rejected") {
    const closureComment = operatorRejectComment || closureReason;
    const detail = closureComment || "No explicit closure comment was recorded.";
    const agentRecText = agentRecLabel(agentRec);
    const operatorAgreed = agentRec === "REJECT"; // operator closed w/o action → agrees with REJECT

    return {
      title: "Incident closed — no action taken",
      lead: closureComment
        ? "The operator closed the incident without CAPA execution."
        : "The incident was closed without CAPA execution.",
      detailLabel: closureComment ? "Closure reason" : "Closure note",
      detail,
      actor: formatDecisionActor(rejectedDecision?.user_id, rejectedDecision?.role) ?? actor,
      tone: "rejected",
      secondaryDetailLabel: agentRecText ? "AI recommendation" : undefined,
      secondaryDetail: agentRecText
        ? `${agentRecText}${operatorAgreed ? " — operator agreed" : " — operator overrode"}`
        : undefined,
    };
  }

  if (action === "approved") {
    const agentRecText = agentRecLabel(agentRec);
    const operatorAgreed = agentRec === "APPROVE";

    return {
      title: "Incident approved for CAPA action",
      lead: "The incident was approved and moved forward for CAPA execution.",
      detailLabel: "Approval note",
      detail: decision?.reason,
      actor,
      tone: "approved",
      secondaryDetailLabel: agentRecText ? "AI recommendation" : undefined,
      secondaryDetail: agentRecText
        ? `${agentRecText}${operatorAgreed ? " — operator agreed" : " — operator overrode"}`
        : undefined,
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
