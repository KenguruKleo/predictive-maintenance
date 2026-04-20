import client from "./client";
import type { StatsSummary } from "../types/stats";

interface RawStatsSummary {
  total_incidents?: number;
  pending_approval?: number;
  escalated?: number;
  resolved?: number;
  recent_decisions?: StatsSummary["recent_decisions"];
  by_status?: Record<string, number>;
  open_incidents?: number;
}

function getStatusCount(byStatus: Record<string, number>, status: string): number {
  const value = byStatus[status];
  return Number.isFinite(value) ? value : 0;
}

function normalizeStatsSummary(data: RawStatsSummary): StatsSummary {
  const byStatus = data.by_status ?? {};
  const resolvedFromStatuses =
    getStatusCount(byStatus, "closed") +
    getStatusCount(byStatus, "completed") +
    getStatusCount(byStatus, "rejected");
  const totalFromStatuses = Object.values(byStatus).reduce(
    (sum, value) => sum + (Number.isFinite(value) ? value : 0),
    0,
  );

  return {
    total_incidents: data.total_incidents ?? totalFromStatuses ?? data.open_incidents ?? 0,
    pending_approval: data.pending_approval ?? getStatusCount(byStatus, "pending_approval"),
    escalated: data.escalated ?? getStatusCount(byStatus, "escalated"),
    resolved: data.resolved ?? resolvedFromStatuses,
    recent_decisions: Array.isArray(data.recent_decisions) ? data.recent_decisions : [],
  };
}

export async function getStats(): Promise<StatsSummary> {
  const { data } = await client.get<RawStatsSummary>("/stats/summary");
  return normalizeStatsSummary(data ?? {});
}
