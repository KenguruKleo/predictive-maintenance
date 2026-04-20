import client from "./client";
import type {
  MarkNotificationsReadResponse,
  NotificationsResponse,
  NotificationSummary,
} from "../types/notification";

interface NotificationFilters {
  status?: "all" | "unread";
  limit?: number;
  incident_id?: string;
}

export async function getNotifications(
  filters: NotificationFilters = {},
): Promise<NotificationsResponse> {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.limit) params.set("limit", String(filters.limit));
  if (filters.incident_id) params.set("incident_id", filters.incident_id);

  const { data } = await client.get<NotificationsResponse>("/notifications", { params });
  return data;
}

export async function getNotificationSummary(): Promise<NotificationSummary> {
  const { data } = await client.get<NotificationSummary>("/notifications/summary");
  return data;
}

export async function markIncidentNotificationsRead(
  incidentId: string,
): Promise<MarkNotificationsReadResponse> {
  const { data } = await client.post<MarkNotificationsReadResponse>(
    `/incidents/${encodeURIComponent(incidentId)}/notifications/read`,
  );
  return data;
}