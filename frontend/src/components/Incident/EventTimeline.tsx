import { useId, useState } from "react";
import type { IncidentEvent } from "../../types/incident";

interface Props {
  events: IncidentEvent[];
  title?: string;
  emptyMessage?: string;
}

// Per-action display metadata: [label, dot-color-class]
const ACTION_META: Record<string, [string, string]> = {
  incident_registered:  ["Incident Registered",   "evt-dot--analyzing"],
  analysis_queued:      ["AI Analysis Queued",    "evt-dot--analyzing"],
  analysis_started:     ["AI Analysis Started",   "evt-dot--analyzing"],
  approval_requested:   ["Awaiting Approval",     "evt-dot--pending"],
  more_info:            ["More Info Requested",   "evt-dot--analyzing"],
  escalated:            ["Escalated",              "evt-dot--escalated"],
  approved:             ["Approved",               "evt-dot--approved"],
  rejected:             ["Rejected",               "evt-dot--rejected"],
  execution_started:    ["Execution Started",      "evt-dot--executing"],
  incident_rejected:    ["Incident Rejected",      "evt-dot--rejected"],
  audit_finalized:      ["Audit Finalized",        "evt-dot--closed"],
  status_updated:       ["Status Updated",         "evt-dot--system"],
};

function formatEventTime(ts: string): string {
  const d = new Date(ts);
  if (isNaN(d.getTime())) return ts;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" })
    + ", "
    + d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
}

function truncate(text: string, max = 160): string {
  return text.length > max ? text.slice(0, max).trimEnd() + "…" : text;
}

function sortNewestFirst<T extends { timestamp: string }>(items: T[]): T[] {
  return [...items].sort((left, right) => {
    const leftTs = Date.parse(left.timestamp);
    const rightTs = Date.parse(right.timestamp);
    if (Number.isNaN(leftTs) || Number.isNaN(rightTs)) {
      return right.timestamp.localeCompare(left.timestamp);
    }
    return rightTs - leftTs;
  });
}

function getEventMeta(action: string): [string, string] {
  return ACTION_META[action] ?? [
    action.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
    "evt-dot--system",
  ];
}

function TimelineEventRow({ event }: { event: IncidentEvent }) {
  const [label, dotCls] = getEventMeta(event.action);

  return (
    <li key={event.id} className={`evt-item evt-item--${event.actor_type}`}>
      <span className={`evt-dot ${dotCls}`} aria-hidden="true" />
      <div className="evt-body">
        <div className="evt-header">
          <span className="evt-label">{label}</span>
          <span className="evt-time">{formatEventTime(event.timestamp)}</span>
        </div>
        <div className="evt-actor">{event.actor}</div>
        {event.details && (
          <div className="evt-details">{truncate(event.details)}</div>
        )}
      </div>
    </li>
  );
}

export default function EventTimeline({
  events,
  title = "Status History",
  emptyMessage = "No status events recorded yet.",
}: Props) {
  const timelineContentId = useId();
  const [isCollapsed, setIsCollapsed] = useState(true);

  // Show only status events; transcript (agent_response, operator_question) lives in AgentChat
  console.debug("[EventTimeline] received", events.length, "events:", events.map((e) => ({ id: e.id, action: e.action, category: e.category })));
  const statusEvents = sortNewestFirst(events).filter(
    (ev) => ev.category !== "transcript" && ev.action !== "agent_response",
  );
  console.debug("[EventTimeline] statusEvents after filter:", statusEvents.length);
  const latestStatusEvent = statusEvents[0];

  return (
    <section className="incident-section">
      <div className="timeline-section-header">
        <h3 className="section-title">{title}</h3>
        {statusEvents.length > 0 && (
          <button
            type="button"
            className="timeline-toggle"
            aria-expanded={!isCollapsed}
            aria-controls={timelineContentId}
            aria-label={isCollapsed ? "Expand status history" : "Collapse status history"}
            title={isCollapsed ? "Expand status history" : "Collapse status history"}
            onClick={() => setIsCollapsed((current) => !current)}
          >
            <svg
              className="timeline-toggle-icon"
              viewBox="0 0 12 12"
              aria-hidden="true"
              focusable="false"
            >
              <path d="M4 2.5L8 6L4 9.5" />
            </svg>
          </button>
        )}
      </div>
      {statusEvents.length === 0 ? (
        <p className="timeline-empty">{emptyMessage}</p>
      ) : (
        <div id={timelineContentId} className="timeline-content">
          <div className={`timeline-view timeline-view--summary${isCollapsed ? " is-active" : ""}`}>
            <ol className="evt-timeline evt-timeline--collapsed">
              {latestStatusEvent && <TimelineEventRow event={latestStatusEvent} />}
            </ol>
          </div>

          <div className={`timeline-view timeline-view--full${!isCollapsed ? " is-active" : ""}`}>
            <ol className="evt-timeline">
              {statusEvents.map((event) => (
                <TimelineEventRow key={event.id} event={event} />
              ))}
            </ol>
          </div>
        </div>
      )}
    </section>
  );
}
