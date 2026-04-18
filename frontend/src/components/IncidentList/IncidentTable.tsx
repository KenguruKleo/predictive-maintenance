import { Link } from "react-router-dom";
import type { Incident } from "../../types/incident";
import SeverityBadge from "./SeverityBadge";
import StatusBadge from "./StatusBadge";

interface Props {
  incidents: Incident[];
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
              <td className="table-cell-title">{inc.title ?? "—"}</td>
              <td>
                <SeverityBadge severity={inc.severity} />
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
              <td colSpan={7} className="table-empty">
                No incidents match your filters.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
