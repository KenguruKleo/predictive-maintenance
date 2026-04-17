import type { Incident, IncidentStatus } from "../../types/incident";
import { Link, useParams } from "react-router-dom";

const STATUS_CONFIG: Record<
  IncidentStatus,
  { icon: string; color: string; text: string }
> = {
  ingested: { icon: "🔵", color: "var(--color-analyzing)", text: "Ingesting..." },
  analyzing: {
    icon: "🔵",
    color: "var(--color-analyzing)",
    text: "AI analyzing...",
  },
  pending_approval: {
    icon: "🟠",
    color: "var(--color-pending)",
    text: "Awaiting decision",
  },
  escalated: {
    icon: "🟡",
    color: "var(--color-escalated)",
    text: "Escalated to QA",
  },
  approved: {
    icon: "🟢",
    color: "var(--color-approved)",
    text: "Approved, executing...",
  },
  rejected: { icon: "🔴", color: "var(--color-rejected)", text: "Rejected" },
  closed: { icon: "⚪", color: "var(--color-closed)", text: "Closed" },
};

interface Props {
  incident: Incident;
}

export default function ActiveIncidentItem({ incident }: Props) {
  const { id } = useParams();
  const isActive = id === incident.id;
  const cfg = STATUS_CONFIG[incident.status];
  const step = incident.workflow_state;

  return (
    <Link
      to={`/incidents/${incident.id}`}
      className={`sidebar-incident-item ${isActive ? "active" : ""}`}
    >
      <div className="sidebar-incident-number">
        {incident.incident_number}
      </div>
      <div className="sidebar-incident-meta">
        {incident.equipment_id}
        {incident.title ? ` · ${incident.title}` : ""}
      </div>
      <div className="sidebar-incident-status" style={{ color: cfg.color }}>
        {cfg.icon}{" "}
        {step && incident.status === "analyzing"
          ? `Step ${step.steps_completed}/${step.total_steps}: ${step.current_step}`
          : cfg.text}
      </div>
    </Link>
  );
}
