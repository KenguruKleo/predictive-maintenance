import { useMemo } from "react";
import type { Incident } from "../../types/incident";
import { groupIncidentsByPeriodAndStatus, getStatusLabel, getPeriodLabel } from "./analyticsUtils";
import { Link } from "react-router-dom";
import "./IncidentAnalytics.css";

interface IncidentAnalyticsProps {
  incidents: Incident[];
}

export default function IncidentAnalytics({ incidents }: IncidentAnalyticsProps) {
  // Group by period (e.g., day) and status
  const grouped = useMemo(() => groupIncidentsByPeriodAndStatus(incidents), [incidents]);

  // Get all unique periods and statuses
  const periods = Object.keys(grouped);
  const statuses = Array.from(
    new Set(periods.flatMap((p) => Object.keys(grouped[p])))
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
                {statuses.map((status) => (
                  <td key={status} className="analytics-count-cell">
                    {grouped[period][status] || 0}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
