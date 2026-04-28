import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { PropsWithChildren } from "react";
import type {
  NotificationsResponse,
  NotificationSummary,
} from "../../src/types/notification";
import { useMarkIncidentNotificationsRead } from "../../src/hooks/useNotifications";

const mockGetNotifications = vi.fn();
const mockGetNotificationSummary = vi.fn();
const mockMarkIncidentNotificationsRead = vi.fn();
const mockMarkAllNotificationsRead = vi.fn();

vi.mock("../../src/api/notifications", () => ({
  getNotifications: (...args: unknown[]) => mockGetNotifications(...args),
  getNotificationSummary: (...args: unknown[]) => mockGetNotificationSummary(...args),
  markIncidentNotificationsRead: (...args: unknown[]) => mockMarkIncidentNotificationsRead(...args),
  markAllNotificationsRead: (...args: unknown[]) => mockMarkAllNotificationsRead(...args),
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

function seedNotifications(queryClient: QueryClient) {
  const allNotifications: NotificationsResponse = {
    items: [
      {
        id: "n-1",
        incident_id: "INC-1",
        type: "incident_pending_approval",
        message: "Incident INC-1 needs review",
        target_role: "qa-manager",
        assigned_to: "qa.user",
        equipment_id: "MIX-102",
        title: "Pending approval",
        incident_status: "pending_approval",
        confidence: 0.8,
        risk_level: "HIGH",
        created_at: "2026-04-28T10:00:00Z",
        updated_at: "2026-04-28T10:00:00Z",
        is_read: false,
        read_at: null,
      },
      {
        id: "n-2",
        incident_id: "INC-2",
        type: "incident_pending_approval",
        message: "Incident INC-2 needs review",
        target_role: "qa-manager",
        assigned_to: "qa.user",
        equipment_id: "MIX-204",
        title: "Pending approval",
        incident_status: "pending_approval",
        confidence: 0.7,
        risk_level: "MEDIUM",
        created_at: "2026-04-28T11:00:00Z",
        updated_at: "2026-04-28T11:00:00Z",
        is_read: false,
        read_at: null,
      },
    ],
    total: 2,
    unread_count: 2,
  };
  const unreadNotifications: NotificationsResponse = {
    ...allNotifications,
    items: [...allNotifications.items],
  };
  const summary: NotificationSummary = {
    unread_count: 2,
    unread_incident_ids: ["INC-1", "INC-2"],
    by_type: {
      incident_pending_approval: 2,
    },
    latest_unread_at: "2026-04-28T11:00:00Z",
  };

  queryClient.setQueryData(["notifications", { status: "all" }], allNotifications);
  queryClient.setQueryData(["notifications", { status: "unread" }], unreadNotifications);
  queryClient.setQueryData(["notifications-summary"], summary);

  return {
    allNotifications,
    unreadNotifications,
    summary,
  };
}

function seedNotificationsWithDuplicateIncident(queryClient: QueryClient) {
  const allNotifications: NotificationsResponse = {
    items: [
      {
        id: "n-1",
        incident_id: "INC-1",
        type: "incident_created",
        message: "Incident INC-1 created",
        target_role: "operator",
        assigned_to: "qa.user",
        equipment_id: "MIX-102",
        title: "Open incident",
        incident_status: "open",
        confidence: 0.8,
        risk_level: "HIGH",
        created_at: "2026-04-28T10:00:00Z",
        updated_at: "2026-04-28T10:00:00Z",
        is_read: false,
        read_at: null,
      },
      {
        id: "n-2",
        incident_id: "INC-1",
        type: "incident_pending_approval",
        message: "Incident INC-1 needs review",
        target_role: "qa-manager",
        assigned_to: "qa.user",
        equipment_id: "MIX-102",
        title: "Pending approval",
        incident_status: "pending_approval",
        confidence: 0.8,
        risk_level: "HIGH",
        created_at: "2026-04-28T10:05:00Z",
        updated_at: "2026-04-28T10:05:00Z",
        is_read: false,
        read_at: null,
      },
      {
        id: "n-3",
        incident_id: "INC-2",
        type: "incident_pending_approval",
        message: "Incident INC-2 needs review",
        target_role: "qa-manager",
        assigned_to: "qa.user",
        equipment_id: "MIX-204",
        title: "Pending approval",
        incident_status: "pending_approval",
        confidence: 0.7,
        risk_level: "MEDIUM",
        created_at: "2026-04-28T11:00:00Z",
        updated_at: "2026-04-28T11:00:00Z",
        is_read: false,
        read_at: null,
      },
    ],
    total: 3,
    unread_count: 3,
  };
  const unreadNotifications: NotificationsResponse = {
    ...allNotifications,
    items: [...allNotifications.items],
  };
  const summary: NotificationSummary = {
    unread_count: 3,
    unread_incident_ids: ["INC-1", "INC-2"],
    by_type: {
      incident_created: 1,
      incident_pending_approval: 2,
    },
    latest_unread_at: "2026-04-28T11:00:00Z",
  };

  queryClient.setQueryData(["notifications", { status: "all" }], allNotifications);
  queryClient.setQueryData(["notifications", { status: "unread" }], unreadNotifications);
  queryClient.setQueryData(["notifications-summary"], summary);
}

describe("useNotifications optimistic updates", () => {
  beforeEach(() => {
    mockGetNotifications.mockReset();
    mockGetNotificationSummary.mockReset();
    mockMarkIncidentNotificationsRead.mockReset();
    mockMarkAllNotificationsRead.mockReset();
  });

  it("updates notification lists and summary optimistically when marking an incident as read", async () => {
    const queryClient = createQueryClient();
    const wrapper = createWrapper(queryClient);
    seedNotifications(queryClient);

    let resolveMutation: (() => void) | undefined;
    const mutationPromise = new Promise<void>((resolve) => {
      resolveMutation = resolve;
    });
    mockMarkIncidentNotificationsRead.mockReturnValueOnce(mutationPromise);

    const hook = renderHook(() => useMarkIncidentNotificationsRead(), { wrapper });

    act(() => {
      hook.result.current.mutate("INC-1");
    });

    await waitFor(() => {
      const allData = queryClient.getQueryData<NotificationsResponse>(["notifications", { status: "all" }]);
      const unreadData = queryClient.getQueryData<NotificationsResponse>(["notifications", { status: "unread" }]);
      const summary = queryClient.getQueryData<NotificationSummary>(["notifications-summary"]);

      expect(allData?.items[0].is_read).toBe(true);
      expect(allData?.unread_count).toBe(1);
      expect(unreadData?.items).toHaveLength(1);
      expect(unreadData?.items[0].incident_id).toBe("INC-2");
      expect(summary?.unread_count).toBe(1);
      expect(summary?.unread_incident_ids).toEqual(["INC-2"]);
    });

    resolveMutation?.();
    await act(async () => {
      await mutationPromise;
    });
  });

  it("decrements notification summary by the number of removed unread notifications", async () => {
    const queryClient = createQueryClient();
    const wrapper = createWrapper(queryClient);
    seedNotificationsWithDuplicateIncident(queryClient);

    let resolveMutation: (() => void) | undefined;
    const mutationPromise = new Promise<void>((resolve) => {
      resolveMutation = resolve;
    });
    mockMarkIncidentNotificationsRead.mockReturnValueOnce(mutationPromise);

    const hook = renderHook(() => useMarkIncidentNotificationsRead(), { wrapper });

    act(() => {
      hook.result.current.mutate("INC-1");
    });

    await waitFor(() => {
      const allData = queryClient.getQueryData<NotificationsResponse>(["notifications", { status: "all" }]);
      const summary = queryClient.getQueryData<NotificationSummary>(["notifications-summary"]);

      expect(allData?.unread_count).toBe(1);
      expect(summary?.unread_count).toBe(1);
      expect(summary?.unread_incident_ids).toEqual(["INC-2"]);
    });

    resolveMutation?.();
    await act(async () => {
      await mutationPromise;
    });
  });

  it("rolls back notification cache updates when the mutation fails", async () => {
    const queryClient = createQueryClient();
    const wrapper = createWrapper(queryClient);
    const seeded = seedNotifications(queryClient);

    let rejectMutation: ((error?: unknown) => void) | undefined;
    const rawMutationPromise = new Promise<void>((_resolve, reject) => {
      rejectMutation = reject;
    });
    mockMarkIncidentNotificationsRead.mockReturnValueOnce(rawMutationPromise);

    const hook = renderHook(() => useMarkIncidentNotificationsRead(), { wrapper });

    let mutationPromise: Promise<unknown> | undefined;
    act(() => {
      mutationPromise = hook.result.current.mutateAsync("INC-1");
    });

    await waitFor(() => {
      const unreadData = queryClient.getQueryData<NotificationsResponse>(["notifications", { status: "unread" }]);
      expect(unreadData?.items).toHaveLength(1);
    });

    rejectMutation?.(new Error("notifications failed"));
    await act(async () => {
      await mutationPromise?.catch(() => undefined);
    });

    await waitFor(() => {
      expect(queryClient.getQueryData(["notifications", { status: "all" }])).toEqual(seeded.allNotifications);
      expect(queryClient.getQueryData(["notifications", { status: "unread" }])).toEqual(seeded.unreadNotifications);
      expect(queryClient.getQueryData(["notifications-summary"])).toEqual(seeded.summary);
    });
  });
});