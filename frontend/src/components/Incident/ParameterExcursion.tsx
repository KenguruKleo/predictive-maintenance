import type { ParameterExcursion as ParamData } from "../../types/incident";

interface Props {
  excursion: ParamData;
}

export default function ParameterExcursion({ excursion }: Props) {
  const { measured_value, unit, parameter, duration_seconds } = excursion;
  const lower = excursion.par_min ?? excursion.lower_limit ?? excursion.nor_min ?? measured_value;
  const upper = excursion.par_max ?? excursion.upper_limit ?? excursion.nor_max ?? measured_value;
  const norMin = excursion.nor_min ?? excursion.lower_limit ?? lower;
  const norMax = excursion.nor_max ?? excursion.upper_limit ?? upper;
  const range = Math.max(upper - lower, 1);
  const norStart = ((norMin - lower) / range) * 100;
  const norWidth = ((norMax - norMin) / range) * 100;
  const valuePos = Math.min(100, Math.max(0, ((measured_value - lower) / range) * 100));
  const inNor = measured_value >= norMin && measured_value <= norMax;
  const inPar = measured_value >= lower && measured_value <= upper;

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
          PAR: {lower}–{upper} {unit}
        </span>
        <span>
          NOR: {norMin}–{norMax} {unit}
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
