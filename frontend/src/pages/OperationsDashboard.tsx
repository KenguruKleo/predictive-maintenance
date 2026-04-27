import { Fragment } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getEquipmentList } from "../api/equipment";
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
  queued_for_analysis: 3,
  ingested: 4,
  open: 5,
  approved: 6,
};

function sortIncidents(items: Incident[]) {
  return [...items].sort(
    (a, b) =>
      (STATUS_ORDER[a.status] ?? 99) - (STATUS_ORDER[b.status] ?? 99),
  );
}

type PipelineStageKey = "ingested" | "analyzing" | "execution";

const PIPELINE_STAGES: Array<{
  key: PipelineStageKey;
  label: string;
  className: string;
  statuses: IncidentStatus[];
}> = [
  {
    key: "ingested",
    label: "Ingested",
    className: "pipeline-stage--ingested",
    statuses: ["ingested"],
  },
  {
    key: "analyzing",
    label: "Analyzing",
    className: "pipeline-stage--analyzing",
    statuses: ["queued_for_analysis", "analyzing", "awaiting_agents"],
  },
  {
    key: "execution",
    label: "Execution",
    className: "pipeline-stage--execution",
    statuses: ["approved", "in_progress"],
  },
];

const PIPELINE_STATUSES = PIPELINE_STAGES.flatMap((stage) => stage.statuses);

function PipelineStatusWidget({ incidents }: { incidents: Incident[] }) {
  const counts: Record<PipelineStageKey, number> = {
    ingested: 0,
    analyzing: 0,
    execution: 0,
  };

  for (const inc of incidents) {
    const stage = PIPELINE_STAGES.find((candidate) => candidate.statuses.includes(inc.status));
    if (stage) counts[stage.key] += 1;
  }

  const visibleStages = PIPELINE_STAGES
    .map((stage) => ({ ...stage, count: counts[stage.key] }))
    .filter((stage) => stage.count > 0);
  const total = visibleStages.reduce((sum, stage) => sum + stage.count, 0);

  return (
    <div className="pipeline-widget">
      <h3 className="pipeline-widget-title">Current Status</h3>
      {total === 0 ? (
        <p className="pipeline-widget-idle">✓ No incidents currently in the active workflow</p>
      ) : (
        <div className="pipeline-stages">
          {visibleStages.map((stage, index) => (
            <Fragment key={stage.key}>
              <div className={`pipeline-stage ${stage.className}`}>
                <span className="pipeline-stage-count">{stage.count}</span>
                <span className="pipeline-stage-label">{stage.label}</span>
              </div>
              {index < visibleStages.length - 1 && (
                <div className="pipeline-stage-arrow" aria-hidden="true">→</div>
              )}
            </Fragment>
          ))}
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
  const {
    data: equipmentData,
    isLoading: isEquipmentLoading,
    error: equipmentError,
  } = useQuery({ queryKey: ["equipment-list"], queryFn: getEquipmentList });
  const { data: pendingData } = useIncidents({ status: "pending_approval" as IncidentStatus, page_size: 20 });
  const { data: escalatedData } = useIncidents({ status: "escalated" as IncidentStatus, page_size: 10 });
  const { data: remoteStats } = useQuery({ queryKey: ["stats"], queryFn: getStats });

  const allIncidents = allData?.items ?? [];
  const equipment = equipmentData ?? [];
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
      {equipmentError && (
        <div className="error-banner">
          Failed to load equipment inventory. Showing assets with active incidents only.
        </div>
      )}

      <EscalationBanner incidents={escalatedIncidents} />

      <StatsCards stats={opsStats} />

      <section className="ops-two-col-shell" aria-label="Pending review and AI pipeline status">
        <div className="ops-two-col">
          <div className="ops-two-col-main">
            <h2 className="section-heading ops-two-col-heading">Action Required — Pending Review</h2>
            <EscalationQueue incidents={pendingIncidents} />
          </div>
          <aside className="ops-two-col-side" aria-label="workflow pipeline sidebar">
            <h2 className="section-heading ops-two-col-heading ops-two-col-side-heading">Workflow Pipeline</h2>
            <PipelineStatusWidget incidents={allIncidents} />
            {aiProcessingCount > 0 && (
              <p className="pipeline-hint">
                {aiProcessingCount} incident{aiProcessingCount !== 1 ? "s" : ""} currently in the AI and execution flow
              </p>
            )}
          </aside>
        </div>
      </section>

      <h2 className="section-heading">Equipment Health</h2>
      <EquipmentHealthGrid
        equipment={equipment}
        incidents={allIncidents}
        isLoading={isEquipmentLoading && equipment.length === 0}
      />

      <IncidentAnalytics incidents={sorted} />

      <h2 className="section-heading">Recent Decisions</h2>
      <RecentDecisions />
    </div>
  );
}
