export interface StatsSummary {
  total_incidents: number;
  pending_approval: number;
  escalated: number;
  resolved: number;
  recent_decisions: RecentDecision[];
}

export interface RecentDecision {
  incident_id: string;
  incident_number: string;
  operator: string;
  decision: "approved" | "rejected";
  ai_confidence: number;
  human_override: boolean;
  decided_at: string;
  response_time_minutes: number;
}
