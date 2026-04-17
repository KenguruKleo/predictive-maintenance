import type { ParameterExcursion as ParamData } from "../../types/incident";

interface Props {
  excursion: ParamData;
}

export default function ParameterExcursion({ excursion }: Props) {
  const { measured_value, nor_min, nor_max, par_min, par_max, unit, parameter, duration_seconds } = excursion;
  const range = par_max - par_min;
  const norStart = ((nor_min - par_min) / range) * 100;
  const norWidth = ((nor_max - nor_min) / range) * 100;
  const valuePos = Math.min(100, Math.max(0, ((measured_value - par_min) / range) * 100));
  const inNor = measured_value >= nor_min && measured_value <= nor_max;
  const inPar = measured_value >= par_min && measured_value <= par_max;

  return (
    <section className="incident-section">
      <h3 className="section-title">Parameter Excursion</h3>
      <div className="excursion-param">{parameter}</div>

      <div className="excursion-bar-container">
        <div className="excursion-bar par-bar">
          <div
            className="excursion-bar nor-bar"
            style={{ left: `${norStart}%`, width: `${norWidth}%` }}
          />
          <div
            className={`excursion-marker ${inNor ? "in-nor" : inPar ? "in-par" : "out-par"}`}
            style={{ left: `${valuePos}%` }}
          />
        </div>
      </div>

      <div className="excursion-labels">
        <span>
          PAR: {par_min}–{par_max} {unit}
        </span>
        <span>
          NOR: {nor_min}–{nor_max} {unit}
        </span>
        <span className={inNor ? "in-nor" : inPar ? "in-par" : "out-par"}>
          Measured: {measured_value} {unit}
        </span>
      </div>
      <div className="excursion-duration">
        Duration: {Math.floor(duration_seconds / 60)}m {duration_seconds % 60}s
      </div>
    </section>
  );
}
