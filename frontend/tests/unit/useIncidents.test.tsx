import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { PropsWithChildren } from "react";
import type { DecisionPayload } from "../../src/types/approval";
import type { Incident, IncidentListResponse } from "../../src/types/incident";
import {
  useIncident,
  useIncidentEvents,
  useIncidents,
  useSubmitDecision,
} from "../../src/hooks/useIncidents";

const mockGetIncidents = vi.fn();
const mockGetIncident = vi.fn();
const mockGetIncidentEvents = vi.fn();
const mockGetIncidentTelemetry = vi.fn();
const mockSubmitDecision = vi.fn();

vi.mock("../../src/api/incidents", () => ({
  getIncidents: (...args: unknown[]) => mockGetIncidents(...args),
  getIncident: (...args: unknown[]) => mockGetIncident(...args),
  getIncidentEvents: (...args: unknown[]) => mockGetIncidentEvents(...args),
  getIncidentTelemetry: (...args: unknown[]) => mockGetIncidentTelemetry(...args),
  submitDecision: (...args: unknown[]) => mockSubmitDecision(...args),
}));

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

function makeIncident(overrides: Partial<Incident> = {}): Incident {
  return {
    id: overrides.id ?? "inc-1",
    equipment_id: overrides.equipment_id ?? "MIX-102",
    severity: overrides.severity ?? "major",
    status: overrides.status ?? "pending_approval",
    incident_number: overrides.incident_number ?? "INC-2026-0001",
    created_at: overrides.created_at ?? "2026-04-28T10:00:00Z",
    updated_at: overrides.updated_at ?? "2026-04-28T10:00:00Z",
    ...overrides,
  };
}

describe("useIncidents optimistic updates", () => {
  beforeEach(() => {
    mockGetIncidents.mockReset();
    mockGetIncident.mockReset();
    mockGetIncidentEvents.mockReset();
    mockGetIncidentTelemetry.mockReset();
    mockSubmitDecision.mockReset();
  });

  it("applies optimistic approved decisions to incident list and detail views", async () => {
    const queryClient = createQueryClient();
    const wrapper = createWrapper(queryClient);
    const baseIncident = makeIncident();
    const baseList: IncidentListResponse = {
      items: [baseIncident],
      total: 1,
      page: 1,
      page_size: 20,
    };
    const approvedPayload: DecisionPayload = {
      action: "approved",
      user_id: "qa.user",
      role: "qa-manager",
      reason: "Evidence confirms the deviation.",
      agent_recommendation: "APPROVE",
    };
    const approvedIncident = makeIncident({
      status: "approved",
      lastDecision: {
        action: "approved",
        user_id: "qa.user",
        role: "qa-manager",
        reason: "Evidence confirms the deviation.",
        agent_recommendation: "APPROVE",
        operator_agrees_with_agent: true,
      },
    });

    mockGetIncidents.mockResolvedValue(baseList);
    mockGetIncident.mockResolvedValue(baseIncident);

    const listHook = renderHook(() => useIncidents({}), { wrapper });
    const detailHook = renderHook(() => useIncident(baseIncident.id), { wrapper });
    const decisionHook = renderHook(() => useSubmitDecision(baseIncident.id), { wrapper });

    await waitFor(() => {
      expect(listHook.result.current.data?.items[0].status).toBe("pending_approval");
      expect(detailHook.result.current.data?.status).toBe("pending_approval");
    });

    let resolveMutation: (() => void) | undefined;
    const mutationPromise = new Promise<void>((resolve) => {
      resolveMutation = resolve;
    });
    mockSubmitDecision.mockReturnValueOnce(mutationPromise);

    act(() => {
      decisionHook.result.current.mutate(approvedPayload);
    });

    await waitFor(() => {
      expect(listHook.result.current.data?.items[0].status).toBe("approved");
      expect(listHook.result.current.data?.items[0].lastDecision?.action).toBe("approved");
      expect(detailHook.result.current.data?.status).toBe("approved");
      expect(detailHook.result.current.data?.lastDecision?.operator_agrees_with_agent).toBe(true);
    });

    mockGetIncidents.mockResolvedValue({ ...baseList, items: [approvedIncident] });
    mockGetIncident.mockResolvedValue(approvedIncident);

    resolveMutation?.();

    await waitFor(() => {
      expect(decisionHook.result.current.isSuccess).toBe(true);
      expect(detailHook.result.current.data?.status).toBe("approved");
      expect(
        queryClient.getQueryData<Record<string, unknown>>(["incident-optimistic-decisions"]),
      ).toEqual({});
    });
  });

  it("optimistically shows more_info status and operator question", async () => {
    const queryClient = createQueryClient();
    const wrapper = createWrapper(queryClient);
    const baseIncident = makeIncident();
    const baseList: IncidentListResponse = {
      items: [baseIncident],
      total: 1,
      page: 1,
      page_size: 20,
    };
    const moreInfoPayload: DecisionPayload = {
      action: "more_info",
      user_id: "operator.user",
      role: "operator",
      question: "Need another SOP excerpt.",
    };
    const awaitingIncident = makeIncident({
      status: "awaiting_agents",
      lastDecision: {
        action: "more_info",
        user_id: "operator.user",
        role: "operator",
        question: "Need another SOP excerpt.",
        operator_agrees_with_agent: null,
      },
    });
    const serverEvent = {
      id: "inc-1-decision-1",
      incident_id: baseIncident.id,
      timestamp: "2026-04-28T10:01:00Z",
      actor: "operator.user",
      actor_type: "human" as const,
      action: "more_info",
      category: "status" as const,
      details: "Need another SOP excerpt.",
      status: "awaiting_agents",
    };

    mockGetIncidents.mockResolvedValue(baseList);
    mockGetIncident.mockResolvedValue(baseIncident);
    mockGetIncidentEvents.mockResolvedValue([]);

    const listHook = renderHook(() => useIncidents({}), { wrapper });
    const detailHook = renderHook(() => useIncident(baseIncident.id), { wrapper });
    const eventsHook = renderHook(() => useIncidentEvents(baseIncident.id), { wrapper });
    const decisionHook = renderHook(() => useSubmitDecision(baseIncident.id), { wrapper });

    await waitFor(() => {
      expect(listHook.result.current.data?.items[0].status).toBe("pending_approval");
      expect(eventsHook.result.current.data).toEqual([]);
    });

    let resolveMutation: (() => void) | undefined;
    const mutationPromise = new Promise<void>((resolve) => {
      resolveMutation = resolve;
    });
    mockSubmitDecision.mockReturnValueOnce(mutationPromise);

    act(() => {
      decisionHook.result.current.mutate(moreInfoPayload);
    });

    await waitFor(() => {
      expect(listHook.result.current.data?.items[0].status).toBe("awaiting_agents");
      expect(detailHook.result.current.data?.status).toBe("awaiting_agents");
      expect(detailHook.result.current.data?.lastDecision?.action).toBe("more_info");
      expect(detailHook.result.current.data?.lastDecision?.question).toBe("Need another SOP excerpt.");
      expect(eventsHook.result.current.data).toEqual(
        expect.arrayContaining([
          expect.objectContaining({
            action: "more_info",
            actor_type: "human",
            details: "Need another SOP excerpt.",
            status: "awaiting_agents",
          }),
        ]),
      );
    });

    mockGetIncidents.mockResolvedValue({ ...baseList, items: [awaitingIncident] });
    mockGetIncident.mockResolvedValue(awaitingIncident);
    mockGetIncidentEvents.mockResolvedValue([serverEvent]);

    resolveMutation?.();

    await waitFor(() => {
      expect(decisionHook.result.current.isSuccess).toBe(true);
      expect(eventsHook.result.current.data).toEqual([serverEvent]);
      expect(
        queryClient.getQueryData<Record<string, unknown>>(["incident-optimistic-decisions"]),
      ).toEqual({});
    });
  });

  it("rolls back optimistic decisions when the mutation fails", async () => {
    const queryClient = createQueryClient();
    const wrapper = createWrapper(queryClient);
    const baseIncident = makeIncident();
    const baseList: IncidentListResponse = {
      items: [baseIncident],
      total: 1,
      page: 1,
      page_size: 20,
    };
    const rejectedPayload: DecisionPayload = {
      action: "rejected",
      user_id: "qa.user",
      role: "qa-manager",
      reason: "Transient sensor noise.",
      agent_recommendation: "REJECT",
    };

    mockGetIncidents.mockResolvedValue(baseList);
    mockGetIncident.mockResolvedValue(baseIncident);

    const listHook = renderHook(() => useIncidents({}), { wrapper });
    const detailHook = renderHook(() => useIncident(baseIncident.id), { wrapper });
    const decisionHook = renderHook(() => useSubmitDecision(baseIncident.id), { wrapper });

    await waitFor(() => {
      expect(listHook.result.current.data?.items[0].status).toBe("pending_approval");
      expect(detailHook.result.current.data?.status).toBe("pending_approval");
    });

    let rejectMutation: ((error?: unknown) => void) | undefined;
    const mutationPromise = new Promise<void>((_resolve, reject) => {
      rejectMutation = reject;
    });
    mockSubmitDecision.mockReturnValueOnce(mutationPromise);

    act(() => {
      void decisionHook.result.current.mutateAsync(rejectedPayload).catch(() => undefined);
    });

    await waitFor(() => {
      expect(listHook.result.current.data?.items[0].status).toBe("rejected");
      expect(detailHook.result.current.data?.status).toBe("rejected");
      expect(detailHook.result.current.data?.lastDecision?.action).toBe("rejected");
    });

    rejectMutation?.(new Error("decision failed"));
    await act(async () => {
      await mutationPromise.catch(() => undefined);
    });

    await waitFor(() => {
      expect(listHook.result.current.data?.items[0].status).toBe("pending_approval");
      expect(listHook.result.current.data?.items[0].lastDecision).toBeUndefined();
      expect(detailHook.result.current.data?.status).toBe("pending_approval");
      expect(detailHook.result.current.data?.lastDecision).toBeUndefined();
    });
  });

  it("rolls back optimistic more_info status and question when the mutation fails", async () => {
    const queryClient = createQueryClient();
    const wrapper = createWrapper(queryClient);
    const baseIncident = makeIncident();
    const baseList: IncidentListResponse = {
      items: [baseIncident],
      total: 1,
      page: 1,
      page_size: 20,
    };
    const moreInfoPayload: DecisionPayload = {
      action: "more_info",
      user_id: "operator.user",
      role: "operator",
      question: "Can we compare this to the previous batch excursion?",
    };

    mockGetIncidents.mockResolvedValue(baseList);
    mockGetIncident.mockResolvedValue(baseIncident);
    mockGetIncidentEvents.mockResolvedValue([]);

    const listHook = renderHook(() => useIncidents({}), { wrapper });
    const detailHook = renderHook(() => useIncident(baseIncident.id), { wrapper });
    const eventsHook = renderHook(() => useIncidentEvents(baseIncident.id), { wrapper });
    const decisionHook = renderHook(() => useSubmitDecision(baseIncident.id), { wrapper });

    await waitFor(() => {
      expect(listHook.result.current.data?.items[0].status).toBe("pending_approval");
      expect(detailHook.result.current.data?.status).toBe("pending_approval");
      expect(eventsHook.result.current.data).toEqual([]);
    });

    let rejectMutation: ((error?: unknown) => void) | undefined;
    const mutationPromise = new Promise<void>((_resolve, reject) => {
      rejectMutation = reject;
    });
    mockSubmitDecision.mockReturnValueOnce(mutationPromise);

    act(() => {
      void decisionHook.result.current.mutateAsync(moreInfoPayload).catch(() => undefined);
    });

    await waitFor(() => {
      expect(listHook.result.current.data?.items[0].status).toBe("awaiting_agents");
      expect(detailHook.result.current.data?.status).toBe("awaiting_agents");
      expect(detailHook.result.current.data?.lastDecision?.question).toBe(
        "Can we compare this to the previous batch excursion?",
      );
      expect(eventsHook.result.current.data).toEqual(
        expect.arrayContaining([
          expect.objectContaining({
            action: "more_info",
            details: "Can we compare this to the previous batch excursion?",
          }),
        ]),
      );
    });

    rejectMutation?.(new Error("follow-up rejected by policy"));
    await act(async () => {
      await mutationPromise.catch(() => undefined);
    });

    await waitFor(() => {
      expect(listHook.result.current.data?.items[0].status).toBe("pending_approval");
      expect(detailHook.result.current.data?.status).toBe("pending_approval");
      expect(detailHook.result.current.data?.lastDecision).toBeUndefined();
      expect(eventsHook.result.current.data).toEqual([]);
      expect(
        queryClient.getQueryData<Record<string, unknown>>(["incident-optimistic-decisions"]),
      ).toEqual({});
    });
  });
});
