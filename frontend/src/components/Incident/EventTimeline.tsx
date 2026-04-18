import type { IncidentEvent } from "../../types/incident";

const ACTOR_ICON: Record<string, string> = {
  system: "⚙️",
  agent: "🤖",
  human: "👤",
};

interface Props {
  events: IncidentEvent[];
}

export default function EventTimeline({ events }: Props) {
  return (
    <section className="incident-section">
      <h3 className="section-title">Timeline / Audit Trail</h3>
      <div className="timeline">
        {events.map((ev) => (
          <div key={ev.id} className={`timeline-item timeline--${ev.actor_type}`}>
            <div className="timeline-dot" />
            <div className="timeline-content">
              <span className="timeline-time">
                {(() => {
                  const d = new Date(ev.timestamp);
                  return isNaN(d.getTime()) ? ev.timestamp : d.toLocaleTimeString();
                })()}
              </span>
              <span className="timeline-actor">
                {ACTOR_ICON[ev.actor_type] ?? "●"} {ev.actor}
              </span>
              <span className="timeline-action">{ev.action}</span>
              <span className="timeline-details">{ev.details}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
