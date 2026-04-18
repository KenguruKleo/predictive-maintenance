import { Link } from "react-router-dom";
import type { Incident } from "../../types/incident";
import SeverityBadge from "./SeverityBadge";

function cardLabel(incident: Incident) {
  if (incident.status === "pending_approval")
    return { text: "ACTION REQUIRED", className: "card-label card-label--action" };
  if (incident.status === "escalated")
    return {
      text: "LOW CONFIDENCE · QA MANAGER NOTIFIED",
      className: "card-label card-label--escalated",
    };
  if (incident.status === "analyzing" || incident.status === "ingested")
    return { text: "AI PROCESSING", className: "card-label card-label--processing" };
  if (incident.status === "approved")
    return { text: "APPROVED · EXECUTING", className: "card-label card-label--approved" };
  return null;
}

function timeAgo(iso?: string) {
  if (!iso) return "unknown time";

  const diff = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diff / 60000);
  if (min < 1) return "just now";
  if (min < 60) return `${min} min ago`;
  const hrs = Math.floor(min / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

interface Props {
  incidents: Incident[];
}

export default function OperationsCards({ incidents }: Props) {
  return (
    <div className="operations-cards">
      {incidents.map((inc) => {
        const label = cardLabel(inc);
        return (
          <div key={inc.id} className="ops-card">
            {label && <div className={label.className}>{label.text}</div>}
            <div className="ops-card-header">
              <span className="ops-card-number">{inc.incident_number}</span>
              <span className="ops-card-equipment">{inc.equipment_id}</span>
              {inc.title && (
                <span className="ops-card-title">{inc.title}</span>
              )}
            </div>
            <div className="ops-card-meta">
              <SeverityBadge severity={inc.severity} />
              {inc.ai_analysis && (
                <>
                  <span className="confidence-pill">
                    Confidence: {Math.round(inc.ai_analysis.confidence * 100)}%
                  </span>
                </>
              )}
            </div>
            {inc.ai_analysis?.root_cause_hypothesis && (
              <div className="ops-card-recommendation">
                AI recommends: {inc.ai_analysis.root_cause_hypothesis}
              </div>
            )}
            <div className="ops-card-footer">
              <span className="ops-card-time">
                {timeAgo(inc.created_at ?? inc.reported_at)}
              </span>
              {(inc.status === "pending_approval" ||
                inc.status === "escalated") && (
                <Link to={`/incidents/${inc.id}`} className="ops-card-action">
                  View & Decide →
                </Link>
              )}
              {inc.status !== "pending_approval" &&
                inc.status !== "escalated" && (
                  <Link
                    to={`/incidents/${inc.id}`}
                    className="ops-card-action secondary"
                  >
                    View Details →
                  </Link>
                )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
