import type { Incident, IncidentStatus } from "../../types/incident";
import { Link, useParams } from "react-router-dom";
import StatusBadge from "../IncidentList/StatusBadge";

const STATUS_CONFIG: Record<
  IncidentStatus,
  { text: string }
> = {
  open: { text: "Open" },
  ingested: { text: "Ingesting..." },
  analyzing: {
    text: "AI analyzing...",
  },
  awaiting_agents: {
    text: "Awaiting agent response",
  },
  pending_approval: {
    text: "Awaiting decision",
  },
  escalated: {
    text: "Escalated to QA",
  },
  approved: {
    text: "Approved, executing...",
  },
  in_progress: {
    text: "Execution in progress",
  },
  executed: {
    text: "Executed",
  },
  completed: {
    text: "Completed",
  },
  rejected: { text: "Rejected" },
  closed: { text: "Closed" },
};

interface Props {
  incident: Incident;
}

function formatSidebarDate(dateStr?: string): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return "";
  const day = d.getDate().toString().padStart(2, "0");
  const mon = d.toLocaleString("en", { month: "short" });
  const hh = d.getHours().toString().padStart(2, "0");
  const mm = d.getMinutes().toString().padStart(2, "0");
  return `${day} ${mon}, ${hh}:${mm}`;
}

export default function ActiveIncidentItem({ incident }: Props) {
  const { id } = useParams();
  const isActive = id === incident.id;
  const cfg = STATUS_CONFIG[incident.status];
  const step = incident.workflow_state;
  const dateLabel = formatSidebarDate(incident.created_at);
  const statusText =
    step && incident.status === "analyzing"
      ? `Step ${step.steps_completed}/${step.total_steps}: ${step.current_step}`
      : cfg.text;

  return (
    <Link
      to={`/incidents/${incident.id}`}
      className={`sidebar-incident-item ${isActive ? "active" : ""}`}
    >
      <div className="sidebar-incident-header">
        <span className="sidebar-incident-number">
          {incident.incident_number ?? incident.id?.slice(0, 12)}
        </span>
        {dateLabel && (
          <span className="sidebar-incident-date">{dateLabel}</span>
        )}
      </div>
      <div className="sidebar-incident-meta">
        <span className="sidebar-incident-equipment">{incident.equipment_id}</span>
        {incident.title && (
          <span className="sidebar-incident-title">{incident.title}</span>
        )}
      </div>
      <div className={`sidebar-incident-status sidebar-incident-status--${incident.status}`}>
        <StatusBadge status={incident.status} />
        <span className="sidebar-incident-status-text">{statusText}</span>
      </div>
    </Link>
  );
}
