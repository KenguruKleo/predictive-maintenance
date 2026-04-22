import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import type { RecentDecision } from "../../types/stats";
import { getStats } from "../../api/stats";
import AiVsHumanBadge from "../Approval/AiVsHumanBadge";
import { useInfiniteDecisions } from "../../hooks/useDecisions";

function AgreementRateKpi({ decisions }: { decisions: RecentDecision[] }) {
  const decided = decisions.filter((d) => d.operator_agrees_with_agent != null);
  if (decided.length === 0) return null;
  const agreed = decided.filter((d) => d.operator_agrees_with_agent === true).length;
  const rate = Math.round((agreed / decided.length) * 100);
  return (
    <div className="agreement-rate-kpi">
      <span className="agreement-rate-kpi-label">AI–Operator agreement</span>
      <strong className={`agreement-rate-kpi-value ${rate >= 70 ? "agreement-rate-kpi-value--good" : "agreement-rate-kpi-value--low"}`}>
        {rate}%
      </strong>
      <span className="agreement-rate-kpi-detail">({agreed}/{decided.length} decisions)</span>
    </div>
  );
}

export default function RecentDecisions() {
  const {
    data,
    isLoading,
    isError,
    isFetchingNextPage,
    fetchNextPage,
    hasNextPage,
  } = useInfiniteDecisions();

  // Fallback: if dedicated endpoint isn't deployed yet, use data from the summary query
  const { data: stats } = useQuery({
    queryKey: ["stats"],
    queryFn: getStats,
    enabled: isError,
  });

  const decisions: RecentDecision[] = isError
    ? (stats?.recent_decisions ?? [])
    : (data?.pages.flatMap((p) => p.items) ?? []);

  const sentinelRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      },
      { threshold: 0.1 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [fetchNextPage, hasNextPage, isFetchingNextPage]);

  if (isLoading && !isError) return <p className="table-loading">Loading decisions…</p>;

  return (
    <div>
      <AgreementRateKpi decisions={decisions} />
      <div className="table-wrapper">
        <table className="incident-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Operator</th>
              <th>Decision</th>
              <th>AI Rec.</th>
              <th>AI Confidence</th>
              <th>Override</th>
              <th>Response Time</th>
            </tr>
          </thead>
          <tbody>
            {decisions.map((d) => (
              <tr key={d.incident_id} className="incident-table-row--clickable" onClick={() => window.location.href = `/incidents/${d.incident_number}`}>
                <td>
                  <Link
                    to={`/incidents/${d.incident_number}`}
                    className="table-id-link"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {d.incident_number}
                  </Link>
                </td>
                <td>{d.operator}</td>
                <td>
                  <span
                    className={`badge badge--${d.decision === "approved" ? "approved" : "rejected"}`}
                  >
                    {d.decision}
                  </span>
                </td>
                <td>
                  <AiVsHumanBadge
                    agentRecommendation={d.agent_recommendation}
                    operatorAgreesWithAgent={d.operator_agrees_with_agent}
                  />
                </td>
                <td>{Math.round(d.ai_confidence * 100)}%</td>
                <td>{d.human_override ? "⚠️ Yes" : "No"}</td>
                <td>{d.response_time_minutes} min</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div ref={sentinelRef} style={{ height: 1 }} />
      {isFetchingNextPage && <p className="table-loading">Loading more…</p>}
    </div>
  );
}

