import { Link, useParams } from "react-router-dom";
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
import type { ParameterExcursion as ParamExcursion } from "../types/incident";

export default function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: incident, isLoading, error } = useIncident(id!);
  const { data: events = [], error: eventsError } = useIncidentEvents(id!);
  if (eventsError) console.warn("[EventTimeline] events fetch failed:", eventsError);
  const { hasAnyRole } = useAuth();

  if (isLoading) return <div className="loading">Loading incident...</div>;
  if (error || !incident)
    return <div className="error-banner">Incident not found.</div>;

  const showApproval =
    hasAnyRole("operator", "qa-manager") &&
    (incident.status === "pending_approval" ||
      incident.status === "escalated" ||
      incident.status === "awaiting_agents");

  const showReadonlyChat =
    !showApproval &&
    events.some(
      (e) =>
        e.action === "operator_question" || e.action === "agent_response",
    );

  // Synthesize parameter_excursion from root-level alert fields for incidents
  // that were ingested before the nested object was added to the payload.
  const excursionData: ParamExcursion | undefined =
    incident.parameter_excursion ??
    (incident.parameter !== undefined || incident.measured_value !== undefined
      ? {
          parameter: incident.parameter ?? "",
          measured_value: incident.measured_value ?? 0,
          unit: incident.unit ?? "",
          duration_seconds: incident.duration_seconds ?? 0,
          lower_limit: incident.lower_limit,
          upper_limit: incident.upper_limit,
        }
      : undefined);

  const canViewTelemetry = hasAnyRole("qa-manager", "it-admin", "auditor");

  // Build a display title from alert fields when incident.title is absent
  const displayTitle = incident.title ?? (() => {
    if (!incident.parameter) return "";
    const label = incident.parameter.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    const { measured_value: m, upper_limit: hi, lower_limit: lo } = incident;
    const dir = m !== undefined && hi !== undefined && m > hi ? "HIGH"
      : m !== undefined && lo !== undefined && m < lo ? "LOW"
      : "Excursion";
    return `${label} ${dir}`;
  })();

  return (
    <div className="page-incident-detail">
      <div className="incident-columns">
        <div className="incident-left">
          <div className="incident-header">
            <Breadcrumb
              items={[
                { label: "Operations Dashboard", to: "/" },
                { label: incident.incident_number ?? incident.id },
              ]}
            />
            <h1 className="incident-title">
              {incident.incident_number ?? incident.id}
              {displayTitle ? ` · ${displayTitle}` : ""}
            </h1>
            <div className="incident-header-meta">
              <StatusBadge status={incident.status} />
              <span>Equipment: {incident.equipment_id}</span>
              {canViewTelemetry && (
                <div className="incident-header-actions">
                  <Link
                    to={`/telemetry?incidentId=${encodeURIComponent(incident.id)}`}
                    className="btn btn--secondary btn--sm"
                  >
                    View Telemetry
                  </Link>
                </div>
              )}
            </div>
          </div>

          <ErrorBoundary inline section="Incident Info">
            <IncidentInfo incident={incident} />
          </ErrorBoundary>

          {excursionData && (
            <ErrorBoundary inline section="Parameter Excursion">
              <ParameterExcursion excursion={excursionData} />
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
        </div>

        <div className="incident-right">
          <ErrorBoundary inline section="Status History">
            <EventTimeline
              events={events}
              title="Status History"
              emptyMessage="No audit events have been recorded for this incident yet."
            />
          </ErrorBoundary>

          {(showApproval || showReadonlyChat) && (
            <ErrorBoundary inline section="Approval Panel">
              <ApprovalPanel incident={incident} events={events} />
            </ErrorBoundary>
          )}

          {!showApproval && !showReadonlyChat && (
            <div className="incident-section">
              <h3 className="section-title">Status</h3>
              <div className="incident-status-block">
                <StatusBadge status={incident.status} />
              </div>
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
