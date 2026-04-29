import { Link } from "react-router-dom";
import type { Incident } from "../../types/incident";
import { isLowConfidenceAnalysis } from "../../utils/analysis";
import SeverityBadge from "../IncidentList/SeverityBadge";
import StatusBadge from "../IncidentList/StatusBadge";

interface Props {
  incidents: Incident[];
}

export default function EscalationQueue({ incidents }: Props) {
  if (incidents.length === 0) {
    return (
      <div className="escalation-empty">No escalated incidents right now.</div>
    );
  }
  return (
    <div className="escalation-queue">
      {incidents.map((inc) => (
        <div key={inc.id} className="escalation-card">
          <div className="escalation-header">
            <span>
              ⚠️ {inc.incident_number} · {inc.equipment_id}
            </span>
            <div className="escalation-badges">
              <StatusBadge status={inc.status} />
              <SeverityBadge severity={inc.severity} />
            </div>
          </div>
          {inc.title && <div className="escalation-title">{inc.title}</div>}
          {inc.ai_analysis && (
            <div className="escalation-reason">
              {isLowConfidenceAnalysis(inc.ai_analysis)
                ? `LOW CONFIDENCE (${Math.round(inc.ai_analysis.confidence * 100)}%)`
                : "Timeout escalation"}
            </div>
          )}
          <Link to={`/incidents/${inc.id}`} className="ops-card-action">
            Review & Decide →
          </Link>
        </div>
      ))}
    </div>
  );
}
