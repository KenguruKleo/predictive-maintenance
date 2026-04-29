import { useQuery, useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getIncidents,
  getIncident,
  getIncidentEvents,
  getIncidentTelemetry,
  submitDecision,
} from "../api/incidents";
import { ACTIVE_INCIDENT_STATUSES } from "../types/incident";
import type {
  Incident,
  IncidentEvent,
  IncidentFilters,
  IncidentListResponse,
  IncidentStatus,
  IncidentTelemetryFilters,
} from "../types/incident";
import type { DecisionPayload } from "../types/approval";

const OPTIMISTIC_INCIDENT_DECISIONS_QUERY_KEY = ["incident-optimistic-decisions"] as const;

interface OptimisticIncidentDecision {
  incidentId: string;
  status: IncidentStatus;
  lastDecision: Incident["lastDecision"];
  updated_at: string;
  events?: IncidentEvent[];
  rejectionReason?: string;
  operatorWorkOrderDraft?: Incident["operatorWorkOrderDraft"];
  operatorAuditEntryDraft?: Incident["operatorAuditEntryDraft"];
}

function useOptimisticIncidentDecisions() {
  return useQuery<Record<string, OptimisticIncidentDecision>>({
    queryKey: OPTIMISTIC_INCIDENT_DECISIONS_QUERY_KEY,
    queryFn: () => ({}),
    initialData: {},
    staleTime: Number.POSITIVE_INFINITY,
    gcTime: Number.POSITIVE_INFINITY,
  });
}

function buildOptimisticIncidentDecision(
  incidentId: string,
  payload: DecisionPayload,
): OptimisticIncidentDecision {
  const agentRecommendation = payload.agent_recommendation;
  const operatorAgreesWithAgent =
    agentRecommendation && (payload.action === "approved" || payload.action === "rejected")
      ? (payload.action === "approved") === (agentRecommendation === "APPROVE")
      : null;

  const updatedAt = new Date().toISOString();
  return {
    incidentId,
    status: getOptimisticIncidentStatus(payload.action),
    lastDecision: {
      action: payload.action,
      user_id: payload.user_id,
      role: payload.role,
      reason: payload.reason,
      question: payload.question,
      agent_recommendation: agentRecommendation,
      operator_agrees_with_agent: operatorAgreesWithAgent,
    },
    updated_at: updatedAt,
    events: buildOptimisticIncidentEvents(incidentId, payload, updatedAt),
    rejectionReason: payload.action === "rejected" ? payload.reason : undefined,
    operatorWorkOrderDraft: payload.work_order_draft as Incident["operatorWorkOrderDraft"],
    operatorAuditEntryDraft: payload.audit_entry_draft as Incident["operatorAuditEntryDraft"],
  };
}

function buildOptimisticIncidentEvents(
  incidentId: string,
  payload: DecisionPayload,
  timestamp: string,
): IncidentEvent[] | undefined {
  if (payload.action !== "more_info" || !payload.question?.trim()) {
    return undefined;
  }

  const eventToken = globalThis.crypto?.randomUUID?.() ??
    `${Date.parse(timestamp)}-${Math.random().toString(36).slice(2)}`;

  return [
    {
      id: `${incidentId}-optimistic-more-info-${eventToken}`,
      incident_id: incidentId,
      timestamp,
      actor: payload.user_id ?? "Operator",
      actor_type: "human",
      action: "more_info",
      category: "status",
      details: payload.question.trim(),
      status: "awaiting_agents",
    },
  ];
}

function getOptimisticIncidentStatus(action: DecisionPayload["action"]): IncidentStatus {
  switch (action) {
    case "approved":
      return "approved";
    case "rejected":
      return "rejected";
    case "more_info":
      return "awaiting_agents";
  }
}

function applyOptimisticDecisionToIncident<T extends Incident | undefined>(
  incident: T,
  optimisticDecision?: OptimisticIncidentDecision,
): T {
  if (!incident || !optimisticDecision) return incident;

  return {
    ...incident,
    status: optimisticDecision.status,
    lastDecision: optimisticDecision.lastDecision,
    updated_at: optimisticDecision.updated_at,
    rejectionReason: optimisticDecision.rejectionReason ?? incident.rejectionReason,
    operatorWorkOrderDraft:
      optimisticDecision.operatorWorkOrderDraft ?? incident.operatorWorkOrderDraft,
    operatorAuditEntryDraft:
      optimisticDecision.operatorAuditEntryDraft ?? incident.operatorAuditEntryDraft,
  } as T;
}

function applyOptimisticDecisionsToIncidentList(
  data: IncidentListResponse | undefined,
  optimisticDecisions: Record<string, OptimisticIncidentDecision>,
): IncidentListResponse | undefined {
  if (!data) return data;

  return {
    ...data,
    items: data.items.map((incident) =>
      applyOptimisticDecisionToIncident(incident, optimisticDecisions[incident.id]),
    ),
  };
}

function applyOptimisticDecisionToIncidentEvents(
  data: IncidentEvent[] | undefined,
  optimisticDecision?: OptimisticIncidentDecision,
): IncidentEvent[] | undefined {
  const optimisticEvents = optimisticDecision?.events;
  if (!optimisticEvents?.length) return data;

  const events = data ?? [];
  const missingEvents = optimisticEvents.filter(
    (optimisticEvent) =>
      !events.some((event) => isSameFollowUpEvent(event, optimisticEvent)),
  );

  return missingEvents.length ? [...events, ...missingEvents] : events;
}

function isSameFollowUpEvent(event: IncidentEvent, optimisticEvent: IncidentEvent) {
  if (event.id === optimisticEvent.id) return true;
  if (event.actor_type !== "human") return false;
  if (event.action !== "more_info" && event.action !== "operator_question") return false;

  return event.details.trim() === optimisticEvent.details.trim();
}

function setOptimisticIncidentDecision(
  queryClient: ReturnType<typeof useQueryClient>,
  incidentId: string,
  optimisticDecision?: OptimisticIncidentDecision,
) {
  queryClient.setQueryData<Record<string, OptimisticIncidentDecision>>(
    OPTIMISTIC_INCIDENT_DECISIONS_QUERY_KEY,
    (current) => {
      const next = { ...(current ?? {}) };
      if (optimisticDecision) {
        next[incidentId] = optimisticDecision;
      } else {
        delete next[incidentId];
      }
      return next;
    },
  );
}

export function useIncidents(filters: IncidentFilters = {}) {
  const optimisticDecisions = useOptimisticIncidentDecisions();
  const incidentsQuery = useQuery({
    queryKey: ["incidents", filters],
    queryFn: () => getIncidents(filters),
  });

  return {
    ...incidentsQuery,
    data: applyOptimisticDecisionsToIncidentList(
      incidentsQuery.data,
      optimisticDecisions.data,
    ),
  };
}

export function useInfiniteActiveIncidents(pageSize = 20) {
  const optimisticDecisions = useOptimisticIncidentDecisions();
  const incidentsQuery = useInfiniteQuery({
    queryKey: ["incidents-active-infinite", pageSize],
    queryFn: ({ pageParam = 1 }) =>
      getIncidents({
        status: ACTIVE_INCIDENT_STATUSES,
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

  return {
    ...incidentsQuery,
    data: incidentsQuery.data
      ? {
          ...incidentsQuery.data,
          pages: incidentsQuery.data.pages.map((page) =>
            applyOptimisticDecisionsToIncidentList(page, optimisticDecisions.data) ?? page,
          ),
        }
      : incidentsQuery.data,
  };
}

export function useIncident(id: string) {
  const optimisticDecisions = useOptimisticIncidentDecisions();
  const incidentQuery = useQuery({
    queryKey: ["incident", id],
    queryFn: () => getIncident(id),
    enabled: !!id,
  });

  return {
    ...incidentQuery,
    data: applyOptimisticDecisionToIncident(
      incidentQuery.data,
      id ? optimisticDecisions.data[id] : undefined,
    ),
  };
}

export function useIncidentEvents(id: string) {
  const optimisticDecisions = useOptimisticIncidentDecisions();
  const eventsQuery = useQuery({
    queryKey: ["incident-events", id],
    queryFn: () => getIncidentEvents(id),
    enabled: !!id,
  });

  return {
    ...eventsQuery,
    data: applyOptimisticDecisionToIncidentEvents(
      eventsQuery.data,
      id ? optimisticDecisions.data[id] : undefined,
    ),
  };
}

export function useIncidentTelemetry(
  id: string,
  filters: IncidentTelemetryFilters = {},
) {
  return useQuery({
    queryKey: ["incident-telemetry", id, filters],
    queryFn: () => getIncidentTelemetry(id, filters),
    enabled: !!id,
  });
}

export function useSubmitDecision(incidentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: DecisionPayload) =>
      submitDecision(incidentId, payload),
    onMutate: async (payload) => {
      await Promise.all([
        queryClient.cancelQueries({ queryKey: ["incident", incidentId] }),
        queryClient.cancelQueries({ queryKey: ["incident-events", incidentId] }),
        queryClient.cancelQueries({ queryKey: ["incidents"] }),
        queryClient.cancelQueries({ queryKey: ["incidents-active-infinite"] }),
      ]);

      const previousOptimisticDecision = queryClient.getQueryData<Record<string, OptimisticIncidentDecision>>(
        OPTIMISTIC_INCIDENT_DECISIONS_QUERY_KEY,
      )?.[incidentId];

      setOptimisticIncidentDecision(
        queryClient,
        incidentId,
        buildOptimisticIncidentDecision(incidentId, payload),
      );

      return { previousOptimisticDecision };
    },
    onError: (_error, _payload, context) => {
      setOptimisticIncidentDecision(queryClient, incidentId, context?.previousOptimisticDecision);
    },
    onSuccess: async () => {
      const syncResults = await Promise.allSettled([
        queryClient.refetchQueries({ queryKey: ["incident", incidentId], exact: true, type: "all" }),
        queryClient.refetchQueries({ queryKey: ["incident-events", incidentId], exact: true, type: "all" }),
        queryClient.refetchQueries({ queryKey: ["incidents"], type: "all" }),
        queryClient.refetchQueries({ queryKey: ["incidents-active-infinite"], type: "all" }),
      ]);

      const failedToSync = syncResults.some((result) => result.status === "rejected");
      if (!failedToSync) {
        setOptimisticIncidentDecision(queryClient, incidentId);
        return;
      }

      queryClient.invalidateQueries({ queryKey: ["incident", incidentId] });
      queryClient.invalidateQueries({ queryKey: ["incident-events", incidentId] });
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      queryClient.invalidateQueries({ queryKey: ["incidents-active-infinite"] });
    },
  });
}
