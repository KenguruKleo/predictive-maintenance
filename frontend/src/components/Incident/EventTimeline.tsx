import type { IncidentEvent } from "../../types/incident";

interface Props {
  events: IncidentEvent[];
  title?: string;
  emptyMessage?: string;
}

// Per-action display metadata: [label, dot-color-class]
const ACTION_META: Record<string, [string, string]> = {
  incident_registered:  ["Incident Registered",   "evt-dot--system"],
  analysis_started:     ["AI Analysis Started",   "evt-dot--agent"],
  approval_requested:   ["Awaiting Approval",      "evt-dot--system"],
  more_info:            ["More Info Requested",    "evt-dot--agent"],
  escalated:            ["Escalated",              "evt-dot--escalated"],
  approved:             ["Approved",               "evt-dot--approved"],
  rejected:             ["Rejected",               "evt-dot--rejected"],
  execution_started:    ["Execution Started",      "evt-dot--agent"],
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

export default function EventTimeline({
  events,
  title = "Status History",
  emptyMessage = "No status events recorded yet.",
}: Props) {
  // Show only status events; transcript (agent_response, operator_question) lives in AgentChat
  console.debug("[EventTimeline] received", events.length, "events:", events.map((e) => ({ id: e.id, action: e.action, category: e.category })));
  const statusEvents = events.filter(
    (ev) => ev.category !== "transcript" && ev.action !== "agent_response",
  );
  console.debug("[EventTimeline] statusEvents after filter:", statusEvents.length);

  return (
    <section className="incident-section">
      <h3 className="section-title">{title}</h3>
      {statusEvents.length === 0 ? (
        <p className="timeline-empty">{emptyMessage}</p>
      ) : (
        <ol className="evt-timeline">
          {statusEvents.map((ev) => {
            const [label, dotCls] = ACTION_META[ev.action] ?? [
              ev.action.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
              "evt-dot--system",
            ];
            return (
              <li key={ev.id} className={`evt-item evt-item--${ev.actor_type}`}>
                <span className={`evt-dot ${dotCls}`} aria-hidden="true" />
                <div className="evt-body">
                  <div className="evt-header">
                    <span className="evt-label">{label}</span>
                    <span className="evt-time">{formatEventTime(ev.timestamp)}</span>
                  </div>
                  <div className="evt-actor">{ev.actor}</div>
                  {ev.details && (
                    <div className="evt-details">{truncate(ev.details)}</div>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
