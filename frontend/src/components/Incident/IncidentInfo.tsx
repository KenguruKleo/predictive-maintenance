import type { Incident } from "../../types/incident";

interface Props {
  incident: Incident;
}

export default function IncidentInfo({ incident }: Props) {
  return (
    <section className="incident-section">
      <h3 className="section-title">Incident Info</h3>
      <dl className="info-grid">
        <dt>Equipment</dt>
        <dd>{incident.equipment_id}</dd>
        <dt>Batch</dt>
        <dd>{incident.batch_id ?? "—"}</dd>
        <dt>Product</dt>
        <dd>{incident.product ?? "—"}</dd>
        <dt>Stage</dt>
        <dd>{incident.production_stage ?? "—"}</dd>
        <dt>Reported</dt>
        <dd>
          {(() => {
            const raw = incident.reported_at ?? incident.created_at;
            if (!raw) return "—";
            const d = new Date(raw);
            return isNaN(d.getTime()) ? "—" : d.toLocaleString();
          })()}
        </dd>
        <dt>Assigned</dt>
        <dd>{incident.assigned_to ?? incident.workflow_state?.assigned_to ?? "Unassigned"}</dd>
      </dl>
    </section>
  );
}
