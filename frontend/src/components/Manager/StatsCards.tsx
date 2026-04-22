import { Activity, Clock, TrendingUp, ShieldCheck } from "lucide-react";
import type { StatsSummary } from "../../types/stats";

interface Props {
  stats: StatsSummary;
}

const CARDS = [
  {
    key: "total_incidents" as const,
    label: "TOTAL",
    Icon: Activity,
    variant: "total",
  },
  {
    key: "pending_approval" as const,
    label: "PENDING",
    Icon: Clock,
    variant: "pending",
  },
  {
    key: "escalated" as const,
    label: "ESCALATED",
    Icon: TrendingUp,
    variant: "escalated",
  },
  {
    key: "resolved" as const,
    label: "RESOLVED",
    Icon: ShieldCheck,
    variant: "resolved",
  },
];

export default function StatsCards({ stats }: Props) {
  return (
    <div className="stats-cards">
      {CARDS.map(({ key, label, Icon, variant }) => (
        <div key={key} className={`stat-card stat-card--${variant}`}>
          <div className="stat-icon-wrap">
            <Icon className="stat-icon-svg" strokeWidth={1.5} />
          </div>
          <span className="stat-value">{stats[key]}</span>
          <span className="stat-label">{label}</span>
        </div>
      ))}
    </div>
  );
}
