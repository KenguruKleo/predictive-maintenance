import type { IncidentStatus, Severity } from "../../types/incident";

interface Props {
  search: string;
  onSearchChange: (v: string) => void;
  status: IncidentStatus | "";
  onStatusChange: (v: IncidentStatus | "") => void;
  severity: Severity | "";
  onSeverityChange: (v: Severity | "") => void;
}

const STATUSES: IncidentStatus[] = [
  "ingested",
  "analyzing",
  "pending_approval",
  "escalated",
  "approved",
  "rejected",
  "closed",
];

const SEVERITIES: Severity[] = ["critical", "major", "moderate", "minor"];

export default function Filters({
  search,
  onSearchChange,
  status,
  onStatusChange,
  severity,
  onSeverityChange,
}: Props) {
  return (
    <div className="filters-bar">
      <input
        type="search"
        className="filter-input"
        placeholder="Search incidents..."
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
      />
      <select
        className="filter-select"
        value={status}
        onChange={(e) => onStatusChange(e.target.value as IncidentStatus | "")}
      >
        <option value="">All statuses</option>
        {STATUSES.map((s) => (
          <option key={s} value={s}>
            {s.replace(/_/g, " ")}
          </option>
        ))}
      </select>
      <select
        className="filter-select"
        value={severity}
        onChange={(e) => onSeverityChange(e.target.value as Severity | "")}
      >
        <option value="">All severities</option>
        {SEVERITIES.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>
    </div>
  );
}
