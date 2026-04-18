import type { ParameterExcursion as ParamData } from "../../types/incident";

interface Props {
  excursion: ParamData;
}

function formatDuration(seconds: number): string {
  if (!seconds) return "—";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function deviationDirection(excursion: ParamData): { label: string; cls: string } | null {
  const { measured_value, lower_limit, upper_limit, nor_min, nor_max, par_min, par_max } = excursion;
  const hi = par_max ?? upper_limit ?? nor_max;
  const lo = par_min ?? lower_limit ?? nor_min;
  if (hi !== undefined && measured_value > hi) return { label: "HIGH", cls: "out-par" };
  if (lo !== undefined && measured_value < lo) return { label: "LOW", cls: "out-par" };
  return null;
}

export default function ParameterExcursion({ excursion }: Props) {
  const { measured_value, unit, parameter, duration_seconds } = excursion;
  const hi = excursion.par_max ?? excursion.upper_limit ?? excursion.nor_max;
  const lo = excursion.par_min ?? excursion.lower_limit ?? excursion.nor_min;
  const dir = deviationDirection(excursion);

  const paramLabel = parameter
    ? parameter.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
    : "Process Parameter";

  return (
    <section className="incident-section">
      <h3 className="section-title">
        Deviation detected
        {dir && <span className={`excursion-badge ${dir.cls}`}>{dir.label}</span>}
      </h3>
      <dl className="info-grid">
        <dt>Parameter</dt>
        <dd>{paramLabel}</dd>
        <dt>Measured</dt>
        <dd className={dir ? dir.cls : ""}>
          {measured_value} {unit}
        </dd>
        {(lo !== undefined || hi !== undefined) && (
          <>
            <dt>Limit range</dt>
            <dd>
              {lo ?? "—"} – {hi ?? "—"} {unit}
            </dd>
          </>
        )}
        {duration_seconds > 0 && (
          <>
            <dt>Duration</dt>
            <dd>{formatDuration(duration_seconds)}</dd>
          </>
        )}
      </dl>
    </section>
  );
}
