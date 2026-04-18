import { useIncidents } from "../hooks/useIncidents";
import IncidentAnalytics from "../components/IncidentAnalytics/IncidentAnalytics";
import Breadcrumb from "../components/Layout/Breadcrumb";
import { ACTIVE_INCIDENT_STATUSES } from "../types/incident";
import type { Incident } from "../types/incident";

const STATUS_ORDER: Record<string, number> = {
  pending_approval: 0,
  escalated: 1,
  analyzing: 2,
  ingested: 3,
  open: 4,
  approved: 5,
};

function sortIncidents(items: Incident[]) {
  return [...items].sort(
    (a, b) =>
      (STATUS_ORDER[a.status] ?? 99) - (STATUS_ORDER[b.status] ?? 99),
  );
}

export default function OperationsDashboard() {
  const { data, isLoading, error } = useIncidents({
    status: [...ACTIVE_INCIDENT_STATUSES],
    page_size: 50,
  });

  const incidents = data?.items ?? [];
  const sorted = sortIncidents(incidents);

  return (
    <div className="page-operations">
      <Breadcrumb items={[{ label: "Operations Dashboard" }]} />
      <h1 className="page-title">Operations Dashboard</h1>
      <p className="page-subtitle">
        {incidents.length} incident{incidents.length !== 1 ? "s" : ""} require
        attention
      </p>

      {isLoading && <div className="loading">Loading incidents...</div>}
      {error && (
        <div className="error-banner">
          Failed to load incidents. Please try again.
        </div>
      )}

      <IncidentAnalytics incidents={sorted} />
    </div>
  );
}
