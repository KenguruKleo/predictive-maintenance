import { useMemo } from "react";
import type { Incident } from "../../types/incident";
import { groupIncidentsByPeriodAndStatus, getStatusLabel, getPeriodLabel, ANALYTICS_STATUSES } from "./analyticsUtils";
import { Link } from "react-router-dom";
import "./IncidentAnalytics.css";

interface IncidentAnalyticsProps {
  incidents: Incident[];
}

export default function IncidentAnalytics({ incidents }: IncidentAnalyticsProps) {
  // Group by period (e.g., day) and status
  const grouped = useMemo(() => groupIncidentsByPeriodAndStatus(incidents), [incidents]);

  const periods = Object.keys(grouped);

  // Only show status columns that have at least one non-zero value across all periods
  const statuses = ANALYTICS_STATUSES.filter((s) =>
    periods.some((p) => (grouped[p][s] ?? 0) > 0)
  );

  return (
    <div className="incident-analytics">
      <h2 className="section-heading">Incident Analytics</h2>
      <div className="analytics-table-wrapper">
        <table className="analytics-table">
          <thead>
            <tr>
              <th>Period</th>
              {statuses.map((status) => (
                <th key={status}>{getStatusLabel(status)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {periods.map((period) => (
              <tr key={period}>
                <td>
                  <Link
                    to={`/history?date_from=${period}&date_to=${period}`}
                    className="analytics-period-link"
                  >
                    {getPeriodLabel(period)}
                  </Link>
                </td>
              {statuses.map((status) => {
                  const count = grouped[period][status] ?? 0;
                  return (
                    <td key={status} className="analytics-count-cell">
                      {count > 0 ? (
                        <Link
                          to={`/history?date_from=${period}&date_to=${period}&status=${encodeURIComponent(status)}`}
                          className="analytics-count-link"
                        >
                          {count}
                        </Link>
                      ) : (
                        0
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
