import type { IncidentTelemetryItem } from "../../types/incident";

interface Props {
  items: IncidentTelemetryItem[];
}

const STATUS_CLASS: Record<string, string> = {
  started: "badge badge--analyzing",
  completed: "badge badge--approved",
  failed: "badge badge--rejected",
};

function formatTimestamp(value: string): string {
  return new Date(value).toLocaleString();
}

export default function IncidentTelemetryTimeline({ items }: Props) {
  if (!items.length) {
    return (
      <div className="telemetry-empty-card">
        No telemetry items matched the current filters.
      </div>
    );
  }

  return (
    <div className="telemetry-timeline">
      {items.map((item) => (
        <article key={item.id} className="telemetry-item-card">
          <div className="telemetry-item-header">
            <div>
              <h3 className="telemetry-item-title">{item.title}</h3>
              <div className="telemetry-item-meta">
                <span>{formatTimestamp(item.timestamp)}</span>
                <span>Round {item.round}</span>
                <span>{item.agent_name}</span>
                <span>{item.trace_kind}</span>
                {item.thread_id ? <span>Thread {item.thread_id}</span> : null}
                {item.run_id ? <span>Run {item.run_id}</span> : null}
              </div>
            </div>
            <div className="telemetry-item-badges">
              <span className={STATUS_CLASS[item.status] ?? "badge badge--closed"}>
                {item.status}
              </span>
              <span className="telemetry-chip">{item.content_type}</span>
              {item.chunk_count > 1 ? (
                <span className="telemetry-chip">{item.chunk_count} chunks</span>
              ) : null}
            </div>
          </div>

          <p className="telemetry-preview">{item.preview || "No preview available."}</p>

          <details className="telemetry-details">
            <summary>View payload</summary>
            <pre className="telemetry-content">{item.content || "No payload captured."}</pre>
          </details>
        </article>
      ))}
    </div>
  );
}