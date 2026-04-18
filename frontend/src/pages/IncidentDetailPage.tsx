import { useParams } from "react-router-dom";
import { useIncident, useIncidentEvents } from "../hooks/useIncidents";
import { useAuth } from "../hooks/useAuth";
import IncidentInfo from "../components/Incident/IncidentInfo";
import ParameterExcursion from "../components/Incident/ParameterExcursion";
import DecisionPackage from "../components/Incident/DecisionPackage";
import BatchDisposition from "../components/Incident/BatchDisposition";
import EventTimeline from "../components/Incident/EventTimeline";
import ApprovalPanel from "../components/Approval/ApprovalPanel";
import StatusBadge from "../components/IncidentList/StatusBadge";
import ErrorBoundary from "../components/ErrorBoundary";
import Breadcrumb from "../components/Layout/Breadcrumb";

export default function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: incident, isLoading, error } = useIncident(id!);
  const { data: events = [] } = useIncidentEvents(id!);
  const { hasAnyRole } = useAuth();

  if (isLoading) return <div className="loading">Loading incident...</div>;
  if (error || !incident)
    return <div className="error-banner">Incident not found.</div>;

  const showApproval =
    hasAnyRole("operator", "qa-manager") &&
    (incident.status === "pending_approval" ||
      incident.status === "escalated");

  const showReadonlyChat =
    !showApproval &&
    events.some(
      (e) =>
        e.action === "operator_question" || e.action === "agent_response",
    );

  return (
    <div className="page-incident-detail">
      <div className="incident-header">
        <Breadcrumb
          items={[
            { label: "Operations Dashboard", to: "/" },
            { label: incident.incident_number ?? incident.id },
          ]}
        />
        <h1 className="incident-title">
          {incident.incident_number ?? incident.id}
          {incident.title ? ` · ${incident.title}` : ""}
        </h1>
        <div className="incident-header-meta">
          <StatusBadge status={incident.status} />
          <span>Equipment: {incident.equipment_id}</span>
        </div>
      </div>

      <div className="incident-columns">
        <div className="incident-left">
          <ErrorBoundary inline section="Incident Info">
            <IncidentInfo incident={incident} />
          </ErrorBoundary>

          {incident.parameter_excursion && (
            <ErrorBoundary inline section="Parameter Excursion">
              <ParameterExcursion excursion={incident.parameter_excursion} />
            </ErrorBoundary>
          )}

          <ErrorBoundary inline section="Decision Package">
            <DecisionPackage incident={incident} />
          </ErrorBoundary>

          <ErrorBoundary inline section="Batch Disposition">
            <BatchDisposition
              batchId={incident.batch_id}
              product={incident.product}
              analysis={incident.ai_analysis}
            />
          </ErrorBoundary>

          <ErrorBoundary inline section="Event Timeline">
            <EventTimeline events={events} />
          </ErrorBoundary>
        </div>

        <div className="incident-right">
          {(showApproval || showReadonlyChat) && (
            <ErrorBoundary inline section="Approval Panel">
              <ApprovalPanel incident={incident} events={events} />
            </ErrorBoundary>
          )}

          {!showApproval && !showReadonlyChat && (
            <div className="incident-section">
              <h3 className="section-title">Status</h3>
              <p className="muted-text">
                {incident.status === "closed"
                  ? "This incident has been closed."
                  : incident.status === "analyzing"
                    ? "AI agents are currently analyzing this incident..."
                    : `Current status: ${incident.status.replace(/_/g, " ")}`}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
