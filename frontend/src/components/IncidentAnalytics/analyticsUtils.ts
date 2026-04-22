import type { Incident } from "../../types/incident";

/**
 * Fixed ordered list of statuses to always show as columns in analytics,
 * regardless of what's actually in the current data set.
 */
export const ANALYTICS_STATUSES = [
  "open",
  "ingested",
  "analyzing",
  "awaiting_agents",
  "pending_approval",
  "escalated",
  "approved",
  "in_progress",
  "executed",
  "completed",
  "rejected",
  "closed",
] as const;

// Group incidents by period (e.g., day) and status
export function groupIncidentsByPeriodAndStatus(
  incidents: Incident[],
  period: "day" | "week" = "day"
): Record<string, Record<string, number>> {
  const grouped: Record<string, Record<string, number>> = {};
  for (const inc of incidents) {
    const rawDate = inc.created_at ?? inc.reported_at;
    if (!rawDate) continue;

    const date = new Date(rawDate);
    if (Number.isNaN(date.getTime())) continue;

    let periodKey = "";
    if (period === "day") {
      periodKey = date.toISOString().slice(0, 10); // YYYY-MM-DD
    } else {
      // Week: YYYY-WW
      const year = date.getFullYear();
      const week = getWeekNumber(date);
      periodKey = `${year}-W${week}`;
    }
    if (!grouped[periodKey]) grouped[periodKey] = {};
    grouped[periodKey][inc.status] = (grouped[periodKey][inc.status] || 0) + 1;
  }
  return grouped;
}

function getWeekNumber(date: Date) {
  const firstDay = new Date(date.getFullYear(), 0, 1);
  const pastDays = Math.floor(
    (date.getTime() - firstDay.getTime()) / 86400000
  );
  return Math.ceil((pastDays + firstDay.getDay() + 1) / 7);
}

export function getStatusLabel(status: string) {
  switch (status) {
    case "open": return "Open";
    case "ingested": return "Ingested";
    case "analyzing": return "Analyzing";
    case "awaiting_agents": return "Awaiting Agents";
    case "pending_approval": return "Pending Approval";
    case "escalated": return "Escalated";
    case "approved": return "Approved";
    case "in_progress": return "In Progress";
    case "executed": return "Executed";
    case "completed": return "Completed";
    case "rejected": return "Rejected";
    case "closed": return "Closed";
    default: return status;
  }
}

export function getPeriodLabel(period: string) {
  // YYYY-MM-DD or YYYY-WW
  if (/^\d{4}-\d{2}-\d{2}$/.test(period)) {
    // Format as '18 Apr 2026'
    const [y, m, d] = period.split("-");
    const date = new Date(Number(y), Number(m) - 1, Number(d));
    return date.toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" });
  }
  if (/^\d{4}-W\d+$/.test(period)) {
    return period.replace("-W", " Week ");
  }
  return period;
}
