import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getNotifications,
  getNotificationSummary,
  markAllNotificationsRead,
  markIncidentNotificationsRead,
} from "../api/notifications";
import type { NotificationsResponse, NotificationSummary } from "../types/notification";

interface NotificationFilters {
  status?: "all" | "unread";
  limit?: number;
  incident_id?: string;
}

interface NotificationQueryOptions {
  enabled?: boolean;
}

export function useNotifications(
  filters: NotificationFilters = {},
  options: NotificationQueryOptions = {},
) {
  const enabled = options.enabled ?? true;

  return useQuery({
    queryKey: ["notifications", filters],
    queryFn: () => getNotifications(filters),
    enabled,
    retry: enabled ? 1 : false,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  });
}

export function useNotificationSummary(options: NotificationQueryOptions = {}) {
  const enabled = options.enabled ?? true;

  return useQuery({
    queryKey: ["notifications-summary"],
    queryFn: () => getNotificationSummary(),
    enabled,
    retry: enabled ? 1 : false,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  });
}

export function useMarkIncidentNotificationsRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (incidentId: string) => markIncidentNotificationsRead(incidentId),
    onMutate: async (incidentId) => {
      await queryClient.cancelQueries({ queryKey: ["notifications"] });
      await queryClient.cancelQueries({ queryKey: ["notifications-summary"] });

      const previousNotificationQueries = queryClient.getQueriesData<NotificationsResponse>({
        queryKey: ["notifications"],
      });
      const previousSummary = queryClient.getQueryData<NotificationSummary>(["notifications-summary"]);

      for (const [queryKey, previousValue] of previousNotificationQueries) {
        if (!previousValue) continue;

        const queryFilters = Array.isArray(queryKey) ? queryKey[1] as { status?: "all" | "unread" } | undefined : undefined;
        const removedCount = previousValue.items.filter((item) => item.incident_id === incidentId).length;
        if (removedCount === 0) continue;

        if (queryFilters?.status === "all") {
          queryClient.setQueryData<NotificationsResponse>(queryKey, {
            ...previousValue,
            items: previousValue.items.map((item) => (
              item.incident_id === incidentId
                ? {
                    ...item,
                    is_read: true,
                    read_at: item.read_at ?? new Date().toISOString(),
                  }
                : item
            )),
            unread_count: Math.max(0, previousValue.unread_count - removedCount),
          });
          continue;
        }

        queryClient.setQueryData<NotificationsResponse>(queryKey, {
          ...previousValue,
          items: previousValue.items.filter((item) => item.incident_id !== incidentId),
          total: Math.max(0, previousValue.total - removedCount),
          unread_count: Math.max(0, previousValue.unread_count - removedCount),
        });
      }

      if (previousSummary) {
        const hadUnreadIncident = previousSummary.unread_incident_ids.includes(incidentId);
        if (hadUnreadIncident) {
          queryClient.setQueryData<NotificationSummary>(["notifications-summary"], {
            ...previousSummary,
            unread_count: Math.max(0, previousSummary.unread_count - 1),
            unread_incident_ids: previousSummary.unread_incident_ids.filter((id) => id !== incidentId),
          });
        }
      }

      return {
        previousNotificationQueries,
        previousSummary,
      };
    },
    onError: (_error, incidentId, context) => {
      for (const [queryKey, previousValue] of context?.previousNotificationQueries ?? []) {
        queryClient.setQueryData(queryKey, previousValue);
      }

      if (context?.previousSummary) {
        queryClient.setQueryData(["notifications-summary"], context.previousSummary);
      }

      queryClient.invalidateQueries({ queryKey: ["incident", incidentId] });
    },
    onSuccess: (_result, incidentId) => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      queryClient.invalidateQueries({ queryKey: ["notifications-summary"] });
      queryClient.invalidateQueries({ queryKey: ["incident", incidentId] });
      queryClient.invalidateQueries({ queryKey: ["incidents-active-infinite"] });
    },
    onSettled: (_result, _error, incidentId) => {
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