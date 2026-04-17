import type { IncidentStatus } from "../../types/incident";

const STATUS_MAP: Record<IncidentStatus, { label: string; className: string }> = {
  ingested: { label: "Ingested", className: "badge badge--analyzing" },
  analyzing: { label: "AI Analyzing", className: "badge badge--analyzing" },
  pending_approval: { label: "Pending Approval", className: "badge badge--pending" },
  escalated: { label: "Escalated", className: "badge badge--escalated" },
  approved: { label: "Approved", className: "badge badge--approved" },
  rejected: { label: "Rejected", className: "badge badge--rejected" },
  closed: { label: "Closed", className: "badge badge--closed" },
};

export default function StatusBadge({ status }: { status: IncidentStatus }) {
  const cfg = STATUS_MAP[status];
  return <span className={cfg.className}>{cfg.label}</span>;
}
