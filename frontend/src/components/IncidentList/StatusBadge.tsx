import type { IncidentStatus } from "../../types/incident";

const STATUS_MAP: Record<IncidentStatus, { label: string; className: string }> = {
  open: { label: "Open", className: "badge badge--analyzing" },
  ingested: { label: "Ingested", className: "badge badge--analyzing" },
  analyzing: { label: "AI Analyzing", className: "badge badge--analyzing" },
  awaiting_agents: { label: "Awaiting Agents", className: "badge badge--analyzing" },
  pending_approval: { label: "Pending Approval", className: "badge badge--pending" },
  escalated: { label: "Escalated", className: "badge badge--escalated" },
  approved: { label: "Approved", className: "badge badge--approved" },
  in_progress: { label: "In Progress", className: "badge badge--analyzing" },
  executed: { label: "Executed", className: "badge badge--approved" },
  completed: { label: "Completed", className: "badge badge--approved" },
  rejected: { label: "Rejected", className: "badge badge--rejected" },
  closed: { label: "Closed", className: "badge badge--closed" },
};

export default function StatusBadge({ status }: { status: IncidentStatus | (string & {}) | null | undefined }) {
  const normalizedStatus = String(status ?? "Unknown");
  const cfg = STATUS_MAP[normalizedStatus as IncidentStatus] ?? {
    label: normalizedStatus.replace(/_/g, " "),
    className: "badge badge--closed",
  };
  return <span className={cfg.className}>{cfg.label}</span>;
}
