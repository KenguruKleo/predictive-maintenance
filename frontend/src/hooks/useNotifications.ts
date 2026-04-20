import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getNotifications,
  getNotificationSummary,
  markAllNotificationsRead,
  markIncidentNotificationsRead,
} from "../api/notifications";

interface NotificationFilters {
  status?: "all" | "unread";
  limit?: number;
  incident_id?: string;
}

export function useNotifications(filters: NotificationFilters = {}) {
  return useQuery({
    queryKey: ["notifications", filters],
    queryFn: () => getNotifications(filters),
    retry: false,
    refetchOnWindowFocus: false,
  });
}

export function useNotificationSummary() {
  return useQuery({
    queryKey: ["notifications-summary"],
    queryFn: () => getNotificationSummary(),
    retry: false,
    refetchOnWindowFocus: false,
  });
}

export function useMarkIncidentNotificationsRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (incidentId: string) => markIncidentNotificationsRead(incidentId),
    onSuccess: (_result, incidentId) => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({ queryKey: ["notifications-summary"] });
      queryClient.invalidateQueries({ queryKey: ["incident", incidentId] });
      queryClient.invalidateQueries({ queryKey: ["incidents-active-infinite"] });
    },
  });
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => markAllNotificationsRead(),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({ queryKey: ["notifications-summary"] });
      queryClient.invalidateQueries({ queryKey: ["incidents-active-infinite"] });

      for (const incidentId of result.incident_ids) {
        queryClient.invalidateQueries({ queryKey: ["incident", incidentId] });
      }
    },
  });
}