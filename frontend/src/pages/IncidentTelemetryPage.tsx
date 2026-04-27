import { useMemo, useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router-dom";
import AgentRunSummary from "../components/Admin/AgentRunSummary";
import IncidentTelemetryTimeline from "../components/Admin/IncidentTelemetryTimeline";
import TelemetryFilters from "../components/Admin/TelemetryFilters";
import Breadcrumb from "../components/Layout/Breadcrumb";
import { useAuth } from "../hooks/useAuth";
import { useIncident, useIncidentEvents, useIncidentTelemetry } from "../hooks/useIncidents";
import { useRoleGuard } from "../hooks/useRoleGuard";
import type {
  AgentTelemetryAgentName,
  AgentTelemetryStatus,
  IncidentTelemetryFilters,
} from "../types/incident";

interface DraftTelemetryFilters {
  searchToken: string;
  incidentId: string;
  agentName: AgentTelemetryAgentName | "";
  status: AgentTelemetryStatus | "";
  round: string;
}

function getStringParam(params: URLSearchParams, key: string): string {
  return params.get(key)?.trim() ?? "";
}

function readDraftFilters(params: URLSearchParams, searchToken: string): DraftTelemetryFilters {
  return {
    searchToken,
    incidentId: getStringParam(params, "incidentId"),
    agentName: getStringParam(params, "agent_name") as AgentTelemetryAgentName | "",
    status: getStringParam(params, "status") as AgentTelemetryStatus | "",
    round: getStringParam(params, "round"),
  };
}

function buildEmptyTelemetryHints(options: {
  hasFilters: boolean;
  incidentStatus?: string;
  businessEventCount: number;
}): string[] {
  const hints = [
    "This view only renders backend-visible Foundry prompt traces captured in App Insights.",
  ];

  if (options.businessEventCount > 0) {
    hints.push(
      `This incident already has ${options.businessEventCount} business events, but those events are stored separately from prompt traces.`,
    );
  }

  if (options.hasFilters) {
    hints.push("Current filters can hide rows. Reset filters to confirm the incident truly has no prompt traces.");
  }

  if (["open", "ingested", "analyzing", "awaiting_agents"].includes(options.incidentStatus ?? "")) {
    hints.push("The incident may not have reached the Foundry agent step yet, so no prompt traces exist to display.");
  } else {
    hints.push("Older incidents created before prompt trace capture was enabled will also appear empty here.");
  }

  return hints;
}

export default function IncidentTelemetryPage() {
  const { allowed, pending } = useRoleGuard(["qa-manager", "it-admin", "auditor"]);
  const { hasAnyRole } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const searchToken = searchParams.toString();
  const activeIncidentId = getStringParam(searchParams, "incidentId");
  const urlDraftFilters = useMemo(
    () => readDraftFilters(searchParams, searchToken),
    [searchParams, searchToken],
  );

  const [draftFilters, setDraftFilters] = useState(urlDraftFilters);
  const activeDraftFilters = draftFilters.searchToken === searchToken ? draftFilters : urlDraftFilters;
  const draftIncidentId = activeDraftFilters.incidentId;
  const draftAgentName = activeDraftFilters.agentName;
  const draftStatus = activeDraftFilters.status;
  const draftRound = activeDraftFilters.round;
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");

  const filters = useMemo<IncidentTelemetryFilters>(() => {
    const roundValue = getStringParam(searchParams, "round");
    return {
      agent_name: (getStringParam(searchParams, "agent_name") as AgentTelemetryAgentName | "") || undefined,
      status: (getStringParam(searchParams, "status") as AgentTelemetryStatus | "") || undefined,
      round: roundValue ? Number(roundValue) : undefined,
    };
  }, [searchParams]);

  const updateDraftFilters = (patch: Partial<Omit<DraftTelemetryFilters, "searchToken">>) => {
    setDraftFilters({ ...activeDraftFilters, ...patch, searchToken });
  };

  const telemetryQuery = useIncidentTelemetry(activeIncidentId, filters);
  const incidentQuery = useIncident(activeIncidentId || "");
  const eventsQuery = useIncidentEvents(activeIncidentId || "");
  const businessEventCount = eventsQuery.data?.length ?? 0;

  if (pending) {
    return <div className="loading">Checking telemetry access...</div>;
  }

  if (!allowed) {
    return <Navigate to="/" replace />;
  }

  const applyFilters = () => {
    const next = new URLSearchParams();
    const trimmedIncidentId = draftIncidentId.trim();
    const trimmedRound = draftRound.trim();

    if (trimmedIncidentId) next.set("incidentId", trimmedIncidentId);
    if (draftAgentName) next.set("agent_name", draftAgentName);
    if (draftStatus) next.set("status", draftStatus);
    if (/^\d+$/.test(trimmedRound)) next.set("round", trimmedRound);

    setSearchParams(next, { replace: true });
  };

  const resetFilters = () => {
    const trimmedIncidentId = draftIncidentId.trim();
    if (!trimmedIncidentId) {
      setSearchParams({}, { replace: true });
      return;
    }

    setSearchParams({ incidentId: trimmedIncidentId }, { replace: true });
  };

  const handleCopyDiagnostics = async () => {
    if (!telemetryQuery.data) return;
    const payload = {
      incident_id: telemetryQuery.data.incident_id,
      summary: telemetryQuery.data.summary,
      query: telemetryQuery.data.query,
      scope: telemetryQuery.data.scope,
      items: telemetryQuery.data.items.slice(-20),
    };

    try {
      await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
      setCopyState("copied");
      window.setTimeout(() => setCopyState("idle"), 1800);
    } catch {
      setCopyState("failed");
      window.setTimeout(() => setCopyState("idle"), 1800);
    }
  };

  return (
    <div className="page-telemetry">
      <Breadcrumb items={[{ label: "Operations Dashboard", to: "/" }, { label: "Incident Telemetry" }]} />
      <div className="telemetry-page-header">
        <div>
          <h1 className="page-title">Incident Telemetry</h1>
          <p className="telemetry-page-subtitle">
            Admin-only backend-visible Foundry trace from App Insights for incident troubleshooting.
          </p>
        </div>
        {activeIncidentId && hasAnyRole("qa-manager", "it-admin", "auditor") ? (
          <Link to={`/incidents/${encodeURIComponent(activeIncidentId)}`} className="btn btn--secondary btn--sm">
            Open Incident Detail
          </Link>
        ) : null}
      </div>

      <div className="telemetry-sticky-bar">
        <TelemetryFilters
          incidentId={draftIncidentId}
          agentName={draftAgentName}
          status={draftStatus}
          round={draftRound}
          onIncidentIdChange={(incidentId) => updateDraftFilters({ incidentId })}
          onAgentNameChange={(agentName) => updateDraftFilters({ agentName })}
          onStatusChange={(status) => updateDraftFilters({ status })}
          onRoundChange={(round) => updateDraftFilters({ round })}
          onApply={applyFilters}
          onReset={resetFilters}
        />
      </div>

      {!activeIncidentId ? (
        <div className="telemetry-empty-card">
          Enter an incident ID to load App Insights telemetry for that incident.
        </div>
      ) : telemetryQuery.isLoading ? (
        <div className="loading">Loading telemetry...</div>
      ) : telemetryQuery.error || !telemetryQuery.data ? (
        <div className="error-banner">Unable to load incident telemetry.</div>
      ) : (
        <>
          {(() => {
            const hasFilters = Boolean(filters.agent_name || filters.status || filters.round !== undefined);
            const isEmpty = telemetryQuery.data.summary.total_items === 0;
            const emptyHints = buildEmptyTelemetryHints({
              hasFilters,
              incidentStatus: incidentQuery.data?.status,
              businessEventCount,
            });

            return (
              <>
          <div className="telemetry-toolbar">
            <span className="telemetry-scope-pill">{telemetryQuery.data.scope.view}</span>
            <button type="button" className="btn btn--secondary btn--sm" onClick={handleCopyDiagnostics}>
              {copyState === "copied"
                ? "Copied"
                : copyState === "failed"
                  ? "Copy Failed"
                  : "Copy Diagnostics"}
            </button>
          </div>

          <AgentRunSummary
            incident={incidentQuery.data}
            summary={telemetryQuery.data.summary}
            businessEventCount={businessEventCount}
          />

          <div className="telemetry-notice-card">
            <h2 className="section-heading">Current Scope</h2>
            <ul className="telemetry-limitations">
              {telemetryQuery.data.scope.limitations.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          {isEmpty ? (
            <div className="telemetry-empty-state">
              <h2 className="section-heading">No Prompt Traces Recorded</h2>
              <p className="telemetry-empty-state-copy">
                App Insights returned zero backend-visible Foundry prompt traces for this incident, so there is no telemetry timeline to render.
              </p>
              <div className="telemetry-empty-state-meta">
                <span>Status: {incidentQuery.data?.status ?? "unknown"}</span>
                <span>Business events: {businessEventCount}</span>
                <span>Last trace: none recorded</span>
              </div>
              <ul className="telemetry-limitations telemetry-limitations--compact">
                {emptyHints.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : (
            <IncidentTelemetryTimeline items={telemetryQuery.data.items} />
          )}
              </>
            );
          })()}
        </>
      )}
    </div>
  );
}