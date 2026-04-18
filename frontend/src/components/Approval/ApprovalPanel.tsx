import { useId, useRef, useState } from "react";
import type { Incident, IncidentEvent } from "../../types/incident";
import { useSubmitDecision } from "../../hooks/useIncidents";
import ConfidenceBanner from "./ConfidenceBanner";
import RejectModal from "./RejectModal";
import AgentChat from "./AgentChat";
import StatusBadge from "../IncidentList/StatusBadge";
import {
  getConfidencePct,
  getRecommendation,
  getRootCause,
  getClassification,
  getDisplayLabel,
} from "../../utils/analysis";

interface Props {
  incident: Incident;
  events: IncidentEvent[];
}

export default function ApprovalPanel({ incident, events }: Props) {
  const [showRejectModal, setShowRejectModal] = useState(false);
  const decision = useSubmitDecision(incident.id);
  const chatInputId = useId();
  const chatInputRef = useRef<HTMLTextAreaElement>(null);
  const isPending =
    incident.status === "pending_approval" ||
    incident.status === "escalated";
  const isAwaitingAgents = incident.status === "awaiting_agents";
  const showRecommendationSummary = Boolean(incident.ai_analysis);
  const dueAt = formatDueAt(incident.workflow_state?.escalation_deadline);
  const confidence = incident.ai_analysis ? getConfidencePct(incident.ai_analysis) : null;
  const recommendation = incident.ai_analysis ? getRecommendation(incident.ai_analysis) : "";
  const rootCause = incident.ai_analysis ? getRootCause(incident.ai_analysis) : "";
  const classification = incident.ai_analysis ? getClassification(incident.ai_analysis) : "";
  const batchImpact = incident.ai_analysis?.batch_disposition
    ? getDisplayLabel(incident.ai_analysis.batch_disposition)
    : "Pending assessment";
  const riskLevel = incident.ai_analysis
    ? getDisplayLabel(incident.ai_analysis.risk_level)
    : "Pending assessment";

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

  const handleNeedMoreInfo = () => {
    chatInputRef.current?.focus();
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
  const panelSubtitle = isAwaitingAgents
    ? "The current recommendation stays visible while the agent prepares the next reply."
    : "Keep the latest recommendation at the top and the conversation below.";

  return (
    <div className="approval-panel approval-panel--sticky">
      <div className="approval-cockpit-header">
        <div>
          <p className="approval-eyebrow">{panelEyebrow}</p>
          <h2 className="approval-cockpit-title">{panelTitle}</h2>
          <p className="approval-cockpit-subtitle">{panelSubtitle}</p>
        </div>
        <StatusBadge status={incident.status} />
      </div>

      <div className="approval-metrics-grid">
        <Metric label="Due by" value={dueAt} />
        <Metric label="Confidence" value={confidence !== null ? `${confidence}%` : "Not available"} />
        <Metric label="Batch impact" value={batchImpact} />
        <Metric label="Risk" value={riskLevel} />
      </div>

      {incident.ai_analysis && <ConfidenceBanner analysis={incident.ai_analysis} />}

      {showRecommendationSummary && (
        <>
          <div className="approval-summary approval-summary--primary">
            <div className="approval-summary-block">
              <span className="approval-summary-label">Recommended action</span>
              <p className="approval-summary-value approval-summary-value--primary">
                {recommendation || "Recommendation is still being prepared."}
              </p>
            </div>

            <div className="approval-summary-columns">
              <div className="approval-summary-block">
                <span className="approval-summary-label">Why this is safe</span>
                <p className="approval-summary-value">
                  {rootCause || "Root-cause evidence is not available yet."}
                </p>
              </div>

              <div className="approval-summary-block approval-summary-block--compact">
                <span className="approval-summary-label">Classification</span>
                <p className="approval-summary-value">{classification || "Pending classification"}</p>
              </div>

              <div className="approval-summary-block approval-summary-block--compact">
                <span className="approval-summary-label">Batch release recommendation</span>
                <p className="approval-summary-value">{batchImpact}</p>
              </div>
            </div>
          </div>
        </>
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

      <AgentChat
        events={events}
        onSend={isPending ? handleAskAgent : undefined}
        readOnly={!isPending}
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

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="approval-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function formatDueAt(value?: string): string {
  if (!value) return "No deadline";
  const dueAt = new Date(value);
  if (Number.isNaN(dueAt.getTime())) return "No deadline";
  return dueAt.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
