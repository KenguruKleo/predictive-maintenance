import { Link } from "react-router-dom";
import type { Incident } from "../../types/incident";
import SeverityBadge from "./SeverityBadge";
import StatusBadge from "./StatusBadge";

interface Props {
  incidents: Incident[];
}

function getIncidentTitle(inc: Incident): string {
  if (inc.title) return inc.title;
  if (inc.parameter) {
    const label = inc.parameter.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    const measured = inc.measured_value;
    const upper = inc.upper_limit;
    const lower = inc.lower_limit;
    const dir =
      measured !== undefined && upper !== undefined && measured > upper
        ? "HIGH"
        : measured !== undefined && lower !== undefined && measured < lower
          ? "LOW"
          : "Excursion";
    return `${label} ${dir}`;
  }
  return "—";
}

function HumanDecisionChip({ action }: { action?: string }) {
  if (!action || action === "more_info") return null;
  const isApproved = action === "approved";
  return (
    <span className={`human-dec-chip human-dec-chip--${isApproved ? "approved" : "rejected"}`}>
      {isApproved ? "✓ APPROVED" : "✕ REJECTED"}
    </span>
  );
}

function AiRecCell({ inc }: { inc: Incident }) {
  const aiRec = inc.ai_analysis?.agent_recommendation;
  if (!aiRec) return <span className="ai-rec-chip ai-rec-chip--none">—</span>;

  const isDecided = inc.status === "approved" || inc.status === "rejected";
  const humanAction = inc.lastDecision?.action ?? inc.finalDecision?.action;
  const isOverride =
    inc.operatorAgreesWithAgent === false ||
    (inc.operatorAgreesWithAgent == null &&
      aiRec != null &&
      humanAction != null &&
      ((humanAction === "rejected" && aiRec === "APPROVE") ||
        (humanAction === "approved" && aiRec === "REJECT")));

  // When operator agreed with the AI, show only the human decision chip (no duplication)
  if (isDecided && !isOverride) {
    return (
      <div className="ai-rec-cell">
        <HumanDecisionChip action={humanAction} />
      </div>
    );
  }

  return (
    <div className="ai-rec-cell">
      <span
        className={`ai-rec-chip ai-rec-chip--${aiRec === "APPROVE" ? "approve" : "reject"}${isOverride ? " ai-rec-chip--overridden" : ""}`}
      >
        {aiRec === "APPROVE" ? "✓ APPROVE" : "✕ REJECT"}
      </span>
      {isDecided && isOverride && <HumanDecisionChip action={humanAction} />}
    </div>
  );
}

export default function IncidentTable({ incidents }: Props) {
  return (
    <div className="table-wrapper">
      <table className="incident-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Equipment</th>
            <th>Title</th>
            <th>Severity</th>
            <th>AI Rec.</th>
            <th>Status</th>
            <th>Batch</th>
            <th>Date</th>
          </tr>
        </thead>
        <tbody>
          {incidents.map((inc) => (
            <tr key={inc.id}>
              <td>
                <Link to={`/incidents/${inc.id}`} className="table-link">
                  {inc.incident_number ?? inc.id}
                </Link>
              </td>
              <td>{inc.equipment_id}</td>
              <td className="table-cell-title">{getIncidentTitle(inc)}</td>
              <td>
                <SeverityBadge severity={inc.severity} />
              </td>
              <td>
                <AiRecCell inc={inc} />
              </td>
              <td>
                <StatusBadge status={inc.status} />
              </td>
              <td>{inc.batch_id ?? "—"}</td>
              <td>
                {(() => {
                  const raw = inc.created_at ?? inc.reported_at;
                  if (!raw) return "—";
                  const d = new Date(raw);
                  if (isNaN(d.getTime())) return "—";
                  return (
                    <span className="table-datetime">
                      <span>{d.toLocaleDateString()}</span>
                      <span className="table-time">{d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                    </span>
                  );
                })()}
              </td>
            </tr>
          ))}
          {incidents.length === 0 && (
            <tr>
              <td colSpan={8} className="table-empty">
                No incidents match your filters.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
