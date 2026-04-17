import type { RecentDecision } from "../../types/stats";

interface Props {
  decisions: RecentDecision[];
}

export default function RecentDecisions({ decisions }: Props) {
  return (
    <div className="table-wrapper">
      <table className="incident-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Operator</th>
            <th>Decision</th>
            <th>AI Confidence</th>
            <th>Override</th>
            <th>Response Time</th>
          </tr>
        </thead>
        <tbody>
          {decisions.map((d) => (
            <tr key={d.incident_id}>
              <td>{d.incident_number}</td>
              <td>{d.operator}</td>
              <td>
                <span
                  className={`badge badge--${d.decision === "approved" ? "approved" : "rejected"}`}
                >
                  {d.decision}
                </span>
              </td>
              <td>{Math.round(d.ai_confidence * 100)}%</td>
              <td>{d.human_override ? "⚠️ Yes" : "No"}</td>
              <td>{d.response_time_minutes} min</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
