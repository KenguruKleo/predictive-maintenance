import { useQuery } from "@tanstack/react-query";
import { getStats } from "../api/stats";
import { useIncidents } from "../hooks/useIncidents";
import Breadcrumb from "../components/Layout/Breadcrumb";
import StatsCards from "../components/Manager/StatsCards";
import EscalationQueue from "../components/Manager/EscalationQueue";
import RecentDecisions from "../components/Manager/RecentDecisions";

export default function ManagerDashboardPage() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["stats"],
    queryFn: getStats,
  });
  const { data: escalated } = useIncidents({ status: "escalated" });

  if (isLoading || !stats) return <div className="loading">Loading...</div>;

  return (
    <div className="page-manager">
      <Breadcrumb items={[{ label: "Operations Dashboard", to: "/" }, { label: "Manager Dashboard" }]} />
      <h1 className="page-title">Manager Dashboard</h1>
      <StatsCards stats={stats} />

      <h2 className="section-heading">Escalation Queue</h2>
      <EscalationQueue incidents={escalated?.items ?? []} />

      <h2 className="section-heading">Recent Decisions</h2>
      <RecentDecisions decisions={stats.recent_decisions} />
    </div>
  );
}
