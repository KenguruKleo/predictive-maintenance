import { useIncidents } from "../hooks/useIncidents";
import { useAuth } from "../hooks/useAuth";
import OperationsCards from "../components/IncidentList/OperationsCards";
import Breadcrumb from "../components/Layout/Breadcrumb";
import type { Incident } from "../types/incident";

const ACTIVE_STATUSES = [
  "ingested",
  "analyzing",
  "pending_approval",
  "escalated",
  "approved",
] as const;

const STATUS_ORDER: Record<string, number> = {
  pending_approval: 0,
  escalated: 1,
  analyzing: 2,
  ingested: 3,
  approved: 4,
};

function sortIncidents(items: Incident[]) {
  return [...items].sort(
    (a, b) =>
      (STATUS_ORDER[a.status] ?? 99) - (STATUS_ORDER[b.status] ?? 99),
  );
}

export default function OperationsDashboard() {
  const { hasRole } = useAuth();
  const { data, isLoading, error } = useIncidents({
    status: [...ACTIVE_STATUSES],
    page_size: 50,
  });

  const incidents = data?.items ?? [];
  const sorted = sortIncidents(incidents);

  const escalated = sorted.filter((i) => i.status === "escalated");
  const rest = sorted.filter((i) => i.status !== "escalated");

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

      {hasRole("qa-manager") && escalated.length > 0 && (
        <>
          <h2 className="section-heading">Escalated to You</h2>
          <OperationsCards incidents={escalated} />
        </>
      )}

      <OperationsCards incidents={hasRole("qa-manager") ? rest : sorted} />
    </div>
  );
}
