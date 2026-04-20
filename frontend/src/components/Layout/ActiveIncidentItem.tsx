import type { Incident } from "../../types/incident";
import { Link, useParams } from "react-router-dom";
import StatusBadge from "../IncidentList/StatusBadge";

interface Props {
  incident: Incident;
  isUnread?: boolean;
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

export default function ActiveIncidentItem({ incident, isUnread = false }: Props) {
  const { id } = useParams();
  const isActive = id === incident.id;
  // Removed unused cfg and step variables after UI deduplication
  const dateLabel = formatSidebarDate(incident.created_at);
  // statusText removed: no longer needed after UI deduplication

  return (
    <Link
      to={`/incidents/${incident.id}`}
      className={`sidebar-incident-item ${isActive ? "active" : ""} ${isUnread ? "sidebar-incident-item--unread" : ""}`}
    >
      <div className="sidebar-incident-header">
        <span className="sidebar-incident-number-wrap">
          {isUnread && <span className="sidebar-incident-unread-dot" aria-hidden="true" />}
          <span className="sidebar-incident-number">
          {incident.incident_number ?? incident.id?.slice(0, 12)}
          </span>
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
      </div>
    </Link>
  );
}
