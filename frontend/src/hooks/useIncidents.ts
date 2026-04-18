import { useQuery, useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getIncidents,
  getIncident,
  getIncidentEvents,
  submitDecision,
} from "../api/incidents";
import type { IncidentFilters } from "../types/incident";
import type { DecisionPayload } from "../types/approval";

export function useIncidents(filters: IncidentFilters = {}) {
  return useQuery({
    queryKey: ["incidents", filters],
    queryFn: () => getIncidents(filters),
  });
}

const ACTIVE_STATUSES: IncidentFilters["status"] = [
  "ingested",
  "analyzing",
  "pending_approval",
  "escalated",
  "approved",
];

export function useInfiniteActiveIncidents(pageSize = 20) {
  return useInfiniteQuery({
    queryKey: ["incidents-active-infinite", pageSize],
    queryFn: ({ pageParam = 1 }) =>
      getIncidents({
        status: ACTIVE_STATUSES,
        page: pageParam as number,
        page_size: pageSize,
        sort_by: "created_at",
        sort_order: "desc",
      }),
    initialPageParam: 1,
    getNextPageParam: (lastPage) => {
      const fetched = (lastPage.page - 1) * lastPage.page_size + lastPage.items.length;
      return fetched < lastPage.total ? lastPage.page + 1 : undefined;
    },
  });
}

export function useIncident(id: string) {
  return useQuery({
    queryKey: ["incident", id],
    queryFn: () => getIncident(id),
    enabled: !!id,
  });
}

export function useIncidentEvents(id: string) {
  return useQuery({
    queryKey: ["incident-events", id],
    queryFn: () => getIncidentEvents(id),
    enabled: !!id,
  });
}

export function useSubmitDecision(incidentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: DecisionPayload) =>
      submitDecision(incidentId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incident", incidentId] });
      queryClient.invalidateQueries({
        queryKey: ["incident-events", incidentId],
      });
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
    },
  });
}
