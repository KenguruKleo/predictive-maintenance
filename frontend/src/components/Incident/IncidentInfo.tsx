import type { Incident } from "../../types/incident";

interface Props {
  incident: Incident;
}

function formatDeviationType(value?: string): string | undefined {
  if (!value) return undefined;
  return value.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatLocation(loc?: string | Record<string, string>): string | undefined {
  if (!loc) return undefined;
  if (typeof loc === "string") return loc === "unknown" ? undefined : loc;
  // Object like {plant, building, room, line}
  const parts = [loc.plant, loc.building, loc.room, loc.line].filter(Boolean);
  return parts.length > 0 ? parts.join(", ") : undefined;
}

export default function IncidentInfo({ incident }: Props) {
  const deviationType = formatDeviationType(incident.deviation_type);
  const locationLabel = formatLocation(incident.location);
  const equipmentLabel =
    incident.equipment_name && incident.equipment_name !== incident.equipment_id
      ? `${incident.equipment_name} (${incident.equipment_id})`
      : incident.equipment_id;

  return (
    <section className="incident-section">
      <h3 className="section-title">Incident Info</h3>
      <dl className="info-grid">
        <dt>Equipment</dt>
        <dd>{equipmentLabel}</dd>
        {incident.equipment_type && incident.equipment_type !== "unknown" && (
          <>
            <dt>Type</dt>
            <dd>{incident.equipment_type}</dd>
          </>
        )}
        {locationLabel && (
          <>
            <dt>Location</dt>
            <dd>{locationLabel}</dd>
          </>
        )}
        {deviationType && (
          <>
            <dt>Deviation Type</dt>
            <dd>{deviationType}</dd>
          </>
        )}
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
