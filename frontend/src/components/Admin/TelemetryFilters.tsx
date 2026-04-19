import type {
  AgentTelemetryAgentName,
  AgentTelemetryStatus,
} from "../../types/incident";

interface Props {
  incidentId: string;
  agentName: AgentTelemetryAgentName | "";
  status: AgentTelemetryStatus | "";
  round: string;
  onIncidentIdChange: (value: string) => void;
  onAgentNameChange: (value: AgentTelemetryAgentName | "") => void;
  onStatusChange: (value: AgentTelemetryStatus | "") => void;
  onRoundChange: (value: string) => void;
  onApply: () => void;
  onReset: () => void;
}

const AGENTS: AgentTelemetryAgentName[] = [
  "orchestrator",
  "research",
  "document",
  "execution",
  "tool",
];

const STATUSES: AgentTelemetryStatus[] = ["started", "completed", "failed"];

export default function TelemetryFilters({
  incidentId,
  agentName,
  status,
  round,
  onIncidentIdChange,
  onAgentNameChange,
  onStatusChange,
  onRoundChange,
  onApply,
  onReset,
}: Props) {
  return (
    <div className="filters-bar telemetry-filters">
      <input
        type="search"
        className="filter-input telemetry-incident-input"
        placeholder="Incident ID (e.g. INC-2026-0008)"
        value={incidentId}
        onChange={(event) => onIncidentIdChange(event.target.value)}
      />
      <select
        className="filter-select"
        value={agentName}
        onChange={(event) => onAgentNameChange(event.target.value as AgentTelemetryAgentName | "")}
      >
        <option value="">All agents</option>
        {AGENTS.map((value) => (
          <option key={value} value={value}>
            {value}
          </option>
        ))}
      </select>
      <select
        className="filter-select"
        value={status}
        onChange={(event) => onStatusChange(event.target.value as AgentTelemetryStatus | "")}
      >
        <option value="">All statuses</option>
        {STATUSES.map((value) => (
          <option key={value} value={value}>
            {value}
          </option>
        ))}
      </select>
      <input
        type="number"
        min="0"
        className="filter-input telemetry-round-input"
        placeholder="Round"
        value={round}
        onChange={(event) => onRoundChange(event.target.value)}
      />
      <button type="button" className="btn btn--primary btn--sm" onClick={onApply}>
        Load Telemetry
      </button>
      <button type="button" className="btn btn--secondary btn--sm" onClick={onReset}>
        Reset
      </button>
    </div>
  );
}