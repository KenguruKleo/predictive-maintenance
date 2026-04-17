import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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
