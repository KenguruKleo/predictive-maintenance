import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useIncidents } from "../hooks/useIncidents";
import { getStats } from "../api/stats";
import IncidentAnalytics from "../components/IncidentAnalytics/IncidentAnalytics";
import Breadcrumb from "../components/Layout/Breadcrumb";
import StatsCards from "../components/Manager/StatsCards";
import EscalationQueue from "../components/Manager/EscalationQueue";
import RecentDecisions from "../components/Manager/RecentDecisions";
import EquipmentHealthGrid from "../components/Operations/EquipmentHealthGrid";
import { ACTIVE_INCIDENT_STATUSES } from "../types/incident";
import type { Incident, IncidentStatus } from "../types/incident";
import type { StatsSummary } from "../types/stats";

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

const PIPELINE_STATUSES: IncidentStatus[] = ["ingested", "analyzing", "awaiting_agents"];

function PipelineStatusWidget({ incidents }: { incidents: Incident[] }) {
  const counts: Record<string, number> = { ingested: 0, analyzing: 0, awaiting_agents: 0 };
  for (const inc of incidents) {
    if (inc.status in counts) counts[inc.status]++;
  }
  const total = Object.values(counts).reduce((s, v) => s + v, 0);

  return (
    <div className="pipeline-widget">
      <h3 className="pipeline-widget-title">AI Pipeline Status</h3>
      {total === 0 ? (
        <p className="pipeline-widget-idle">✓ No incidents currently in AI pipeline</p>
      ) : (
        <div className="pipeline-stages">
          <div className="pipeline-stage pipeline-stage--ingested">
            <span className="pipeline-stage-count">{counts.ingested}</span>
            <span className="pipeline-stage-label">Ingested</span>
          </div>
          <div className="pipeline-stage-arrow">→</div>
          <div className="pipeline-stage pipeline-stage--analyzing">
            <span className="pipeline-stage-count">{counts.analyzing}</span>
            <span className="pipeline-stage-label">Analyzing</span>
          </div>
          <div className="pipeline-stage-arrow">→</div>
          <div className="pipeline-stage pipeline-stage--awaiting">
            <span className="pipeline-stage-count">{counts.awaiting_agents}</span>
            <span className="pipeline-stage-label">Awaiting Agents</span>
          </div>
        </div>
      )}
    </div>
  );
}

function EscalationBanner({ incidents }: { incidents: Incident[] }) {
  if (incidents.length === 0) return null;
  return (
    <div className="escalation-banner">
      <span className="escalation-banner-icon">⚠️</span>
      <span className="escalation-banner-text">
        <strong>{incidents.length} incident{incidents.length !== 1 ? "s" : ""} escalated</strong>
        {" "}— QA Manager has been notified. Your review is required.
      </span>
      <Link to="/history?status=escalated" className="escalation-banner-link">
        View escalated →
      </Link>
    </div>
  );
}

export default function OperationsDashboard() {
  const { data: allData, isLoading, error } = useIncidents({
    status: [...ACTIVE_INCIDENT_STATUSES],
    page_size: 100,
  });
  const { data: pendingData } = useIncidents({ status: "pending_approval" as IncidentStatus, page_size: 20 });
  const { data: escalatedData } = useIncidents({ status: "escalated" as IncidentStatus, page_size: 10 });
  const { data: remoteStats } = useQuery({ queryKey: ["stats"], queryFn: getStats });

  const allIncidents = allData?.items ?? [];
  const pendingIncidents = pendingData?.items ?? [];
  const escalatedIncidents = escalatedData?.items ?? [];
  const sorted = sortIncidents(allIncidents);

  const aiProcessingCount = allIncidents.filter((i) =>
    (PIPELINE_STATUSES as string[]).includes(i.status)
  ).length;

  const opsStats: StatsSummary = {
    total_incidents: allData?.total ?? allIncidents.length,
    pending_approval: pendingData?.total ?? pendingIncidents.length,
    escalated: escalatedData?.total ?? escalatedIncidents.length,
    resolved: remoteStats?.resolved ?? 0,
    recent_decisions: remoteStats?.recent_decisions ?? [],
  };

  return (
    <div className="page-operations">
      <Breadcrumb items={[{ label: "Operations Dashboard" }]} />
      <h1 className="page-title">Operations Dashboard</h1>

      {isLoading && <div className="loading">Loading incidents...</div>}
      {error && (
        <div className="error-banner">
          Failed to load incidents. Please try again.
        </div>
      )}

      <EscalationBanner incidents={escalatedIncidents} />

      <StatsCards stats={opsStats} />

      <div className="ops-two-col">
        <div className="ops-two-col-main">
          <h2 className="section-heading">Action Required — Pending Review</h2>
          <EscalationQueue incidents={pendingIncidents} />
        </div>
        <div className="ops-two-col-side">
          <PipelineStatusWidget incidents={allIncidents} />
          {aiProcessingCount > 0 && (
            <p className="pipeline-hint">
              {aiProcessingCount} incident{aiProcessingCount !== 1 ? "s" : ""} currently being processed by AI agents
            </p>
          )}
        </div>
      </div>

      <h2 className="section-heading">Equipment Health</h2>
      <EquipmentHealthGrid incidents={allIncidents} />

      <IncidentAnalytics incidents={sorted} />

      <h2 className="section-heading">Recent Decisions</h2>
      <RecentDecisions />
    </div>
  );
}
