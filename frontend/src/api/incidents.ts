import client from "./client";
import type {
  Incident,
  IncidentEvent,
  IncidentFilters,
  IncidentListResponse,
  IncidentTelemetryFilters,
  IncidentTelemetryResponse,
} from "../types/incident";
import type { DecisionPayload } from "../types/approval";
import { getE2EDecisionDefaults, IS_E2E_AUTH } from "../authRuntime";

export async function getIncidents(
  filters: IncidentFilters = {},
): Promise<IncidentListResponse> {
  const params = new URLSearchParams();
  if (filters.status) {
    const statuses = Array.isArray(filters.status)
      ? filters.status
      : [filters.status];
    statuses.forEach((s) => params.append("status", s));
  }
  if (filters.severity) params.set("severity", filters.severity);
  if (filters.equipment_id) params.set("equipment_id", filters.equipment_id);
  if (filters.search) params.set("search", filters.search);
  if (filters.page) params.set("page", String(filters.page));
  if (filters.page_size) params.set("page_size", String(filters.page_size));
  if (filters.date_from) params.set("date_from", filters.date_from);
  if (filters.date_to) params.set("date_to", filters.date_to);
  if (filters.sort_by) params.set("sort_by", filters.sort_by);
  if (filters.sort_order) params.set("sort_order", filters.sort_order);
  const { data } = await client.get<IncidentListResponse>("/incidents", {
    params,
  });
  return data;
}

export async function getIncident(id: string): Promise<Incident> {
  const { data } = await client.get<Incident>(`/incidents/${encodeURIComponent(id)}`);
  return data;
}

export async function getIncidentEvents(
  id: string,
): Promise<IncidentEvent[]> {
  const { data } = await client.get<{ events: IncidentEvent[] } | IncidentEvent[]>(
    `/incidents/${encodeURIComponent(id)}/events`,
  );
  // Backend wraps events in { incident_id, events, total }
  if (data && !Array.isArray(data) && Array.isArray((data as { events: IncidentEvent[] }).events)) {
    return (data as { events: IncidentEvent[] }).events;
  }
  return Array.isArray(data) ? data : [];
}

export async function getIncidentTelemetry(
  id: string,
  filters: IncidentTelemetryFilters = {},
): Promise<IncidentTelemetryResponse> {
  const params = new URLSearchParams();
  if (filters.agent_name) params.set("agent_name", filters.agent_name);
  if (filters.status) params.set("status", filters.status);
  if (filters.round !== undefined) params.set("round", String(filters.round));

  const { data } = await client.get<IncidentTelemetryResponse>(
    `/incidents/${encodeURIComponent(id)}/agent-telemetry`,
    { params },
  );
  return data;
}

export async function submitDecision(
  id: string,
  payload: DecisionPayload,
): Promise<void> {
  const e2eDecisionDefaults = IS_E2E_AUTH ? getE2EDecisionDefaults() : null;

  await client.post(`/incidents/${encodeURIComponent(id)}/decision`, {
    ...payload,
    user_id: payload.user_id ?? e2eDecisionDefaults?.userId ?? "ivan.petrenko",
    role: payload.role ?? e2eDecisionDefaults?.role ?? "operator",
  });
}
