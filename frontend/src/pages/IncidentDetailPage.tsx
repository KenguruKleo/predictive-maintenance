import { useParams, Link } from "react-router-dom";
import { useIncident, useIncidentEvents } from "../hooks/useIncidents";
import { useAuth } from "../hooks/useAuth";
import IncidentInfo from "../components/Incident/IncidentInfo";
import ParameterExcursion from "../components/Incident/ParameterExcursion";
import AiAnalysis from "../components/Incident/AiAnalysis";
import EvidenceCitations from "../components/Incident/EvidenceCitations";
import DocumentPreviews from "../components/Incident/DocumentPreviews";
import BatchDisposition from "../components/Incident/BatchDisposition";
import EventTimeline from "../components/Incident/EventTimeline";
import ApprovalPanel from "../components/Approval/ApprovalPanel";
import StatusBadge from "../components/IncidentList/StatusBadge";

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
        <Link to="/" className="back-link">
          ← Back
        </Link>
        <h1 className="incident-title">
          {incident.incident_number}
          {incident.title ? ` · ${incident.title}` : ""}
        </h1>
        <div className="incident-header-meta">
          <StatusBadge status={incident.status} />
          <span>Equipment: {incident.equipment_id}</span>
        </div>
      </div>

      <div className="incident-columns">
        <div className="incident-left">
          <IncidentInfo incident={incident} />

          {incident.parameter_excursion && (
            <ParameterExcursion excursion={incident.parameter_excursion} />
          )}

          {incident.ai_analysis && (
            <AiAnalysis analysis={incident.ai_analysis} />
          )}

          {incident.ai_analysis?.evidence_citations && (
            <EvidenceCitations
              citations={incident.ai_analysis.evidence_citations}
            />
          )}

          {incident.document_drafts && incident.document_drafts.length > 0 && (
            <DocumentPreviews drafts={incident.document_drafts} />
          )}

          <BatchDisposition
            batchId={incident.batch_id}
            product={incident.product}
            analysis={incident.ai_analysis}
          />

          <EventTimeline events={events} />
        </div>

        <div className="incident-right">
          {(showApproval || showReadonlyChat) && (
            <ApprovalPanel incident={incident} events={events} />
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
