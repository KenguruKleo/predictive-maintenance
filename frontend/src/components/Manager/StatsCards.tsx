import type { StatsSummary } from "../../types/stats";

interface Props {
  stats: StatsSummary;
}

export default function StatsCards({ stats }: Props) {
  const cards = [
    { label: "Total", value: stats.total_incidents, icon: "📊" },
    { label: "Pending", value: stats.pending_approval, icon: "⏳" },
    { label: "Escalated", value: stats.escalated, icon: "⏫" },
    { label: "Resolved", value: stats.resolved, icon: "✅" },
  ];
  return (
    <div className="stats-cards">
      {cards.map((c) => (
        <div key={c.label} className="stat-card">
          <span className="stat-icon">{c.icon}</span>
          <span className="stat-value">{c.value}</span>
          <span className="stat-label">{c.label}</span>
        </div>
      ))}
    </div>
  );
}
