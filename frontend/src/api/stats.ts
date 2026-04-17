import client from "./client";
import type { StatsSummary } from "../types/stats";

export async function getStats(): Promise<StatsSummary> {
  const { data } = await client.get<StatsSummary>("/stats/summary");
  return data;
}
