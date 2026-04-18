import type { IncidentEvent } from "../../types/incident";
import { labelize } from "../../utils/analysis";

interface Props {
  events: IncidentEvent[];
  title?: string;
  emptyMessage?: string;
  compact?: boolean;
}

export default function EventTimeline({
  events,
  title = "Timeline / Audit Trail",
  emptyMessage = "No audit events recorded yet.",
  compact = false,
}: Props) {
  return (
    <section className={`incident-section ${compact ? "incident-section--compact" : ""}`}>
      <h3 className="section-title">{title}</h3>
      <div className={`timeline ${compact ? "timeline--compact" : ""}`}>
        {events.length === 0 && <p className="timeline-empty">{emptyMessage}</p>}
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
              <span className="timeline-actor">{ev.actor}</span>
              <span className="timeline-action">{labelize(ev.action)}</span>
              <span className="timeline-details">{ev.details}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
