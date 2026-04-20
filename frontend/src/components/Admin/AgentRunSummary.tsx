import type { Incident, IncidentTelemetrySummary } from "../../types/incident";
import StatusBadge from "../IncidentList/StatusBadge";

interface Props {
  incident?: Incident;
  summary: IncidentTelemetrySummary;
  businessEventCount: number;
}

function formatDuration(value?: number | null): string {
  if (!value) return "n/a";
  if (value < 1000) return `${value} ms`;
  return `${(value / 1000).toFixed(1)} s`;
}

function formatTimestamp(value?: string | null): string {
  if (!value) return "n/a";
  return new Date(value).toLocaleString();
}

export default function AgentRunSummary({ incident, summary, businessEventCount }: Props) {
  return (
    <div className="telemetry-summary-wrap">
      {incident && (
        <div className="telemetry-incident-card">
          <div>
            <div className="telemetry-incident-title">{incident.incident_number ?? incident.id}</div>
            <div className="telemetry-incident-subtitle">
              {incident.title ?? incident.equipment_id}
            </div>
          </div>
          <div className="telemetry-incident-meta">
            <StatusBadge status={incident.status} />
            <span>Equipment: {incident.equipment_id}</span>
          </div>
        </div>
      )}

      <div className="telemetry-summary-grid">
        <div className="telemetry-stat-card">
          <span className="telemetry-stat-label">Trace Items</span>
          <strong className="telemetry-stat-value">{summary.total_items}</strong>
        </div>
        <div className="telemetry-stat-card">
          <span className="telemetry-stat-label">Completed</span>
          <strong className="telemetry-stat-value">{summary.completed_items}</strong>
        </div>
        <div className="telemetry-stat-card">
          <span className="telemetry-stat-label">Started</span>
          <strong className="telemetry-stat-value">{summary.started_items}</strong>
        </div>
        <div className="telemetry-stat-card telemetry-stat-card--danger">
          <span className="telemetry-stat-label">Failed</span>
          <strong className="telemetry-stat-value">{summary.failed_items}</strong>
        </div>
        <div className="telemetry-stat-card">
          <span className="telemetry-stat-label">Rounds</span>
          <strong className="telemetry-stat-value">
            {summary.rounds.length ? summary.rounds.join(", ") : "n/a"}
          </strong>
        </div>
        <div className="telemetry-stat-card">
          <span className="telemetry-stat-label">Duration</span>
          <strong className="telemetry-stat-value">{formatDuration(summary.total_duration_ms)}</strong>
        </div>
        <div className="telemetry-stat-card">
          <span className="telemetry-stat-label">Business Events</span>
          <strong className="telemetry-stat-value">{businessEventCount}</strong>
        </div>
        <div className="telemetry-stat-card">
          <span className="telemetry-stat-label">Last Trace</span>
          <strong className="telemetry-stat-value telemetry-stat-value--sm">
            {formatTimestamp(summary.last_timestamp)}
          </strong>
        </div>
        {summary.total_tokens != null && (
          <>
            <div className="telemetry-stat-card">
              <span className="telemetry-stat-label">Prompt Tokens</span>
              <strong className="telemetry-stat-value">
                {summary.total_prompt_tokens?.toLocaleString() ?? "n/a"}
              </strong>
            </div>
            <div className="telemetry-stat-card">
              <span className="telemetry-stat-label">Completion Tokens</span>
              <strong className="telemetry-stat-value">
                {summary.total_completion_tokens?.toLocaleString() ?? "n/a"}
              </strong>
            </div>
            <div className="telemetry-stat-card">
              <span className="telemetry-stat-label">Total Tokens</span>
              <strong className="telemetry-stat-value">
                {summary.total_tokens.toLocaleString()}
              </strong>
            </div>
          </>
        )}
      </div>
    </div>
  );
}