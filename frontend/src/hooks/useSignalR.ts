import { useEffect, useRef, useState, useCallback } from "react";
import {
  HubConnection,
  HubConnectionBuilder,
  LogLevel,
} from "@microsoft/signalr";
import { InteractionStatus } from "@azure/msal-browser";
import { useMsal } from "@azure/msal-react";
import { useQueryClient } from "@tanstack/react-query";
import client from "../api/client";
import { API_BASE_URL } from "../authConfig";
import { IS_E2E_AUTH } from "../authRuntime";
import type { BrowserNotificationPermission } from "../types/notification";

export interface Toast {
  id: string;
  message: string;
  type: "info" | "warning" | "success" | "error";
  timestamp: number;
}

function getBrowserNotificationPermission(): BrowserNotificationPermission {
  if (typeof window === "undefined" || !("Notification" in window)) {
    return "unsupported";
  }
  return Notification.permission;
}

export function useSignalR() {
  const { accounts, inProgress, instance } = useMsal();
  const connectionRef = useRef<HubConnection | null>(null);
  const registeredConnectionIdRef = useRef<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [browserPermission, setBrowserPermission] = useState<BrowserNotificationPermission>(() => getBrowserNotificationPermission());
  const queryClient = useQueryClient();
  const authReady = IS_E2E_AUTH || (inProgress === InteractionStatus.None && Boolean(instance.getActiveAccount() ?? accounts[0]));

  const addToast = useCallback(
    (message: string, type: Toast["type"] = "info") => {
      const toast: Toast = {
        id: crypto.randomUUID(),
        message,
        type,
        timestamp: Date.now(),
      };
      setToasts((prev) => [...prev.slice(-9), toast]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== toast.id));
      }, 6000);
    },
    [],
  );

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const registerConnectionGroups = useCallback(async (connectionId?: string | null) => {
    if (!connectionId || !authReady || registeredConnectionIdRef.current === connectionId) {
      return;
    }

    try {
      await client.post("/signalr/register", { connection_id: connectionId });
      registeredConnectionIdRef.current = connectionId;
    } catch {
      // SignalR registration is best-effort; query refetch still keeps UI consistent.
      registeredConnectionIdRef.current = null;
    }
  }, [authReady]);

  useEffect(() => {
    const connectionId = connectionRef.current?.connectionId;
    if (!connected || !connectionId || !authReady) {
      return;
    }

    void registerConnectionGroups(connectionId);
  }, [authReady, connected, registerConnectionGroups]);

  const invalidateLiveIncidentViews = useCallback((incidentId?: string) => {
    queryClient.invalidateQueries({ queryKey: ["incidents"] });
    queryClient.invalidateQueries({ queryKey: ["incidents-active-infinite"] });
    queryClient.invalidateQueries({ queryKey: ["notifications"] });
    queryClient.invalidateQueries({ queryKey: ["notifications-summary"] });
    if (incidentId) {
      queryClient.invalidateQueries({ queryKey: ["incident", incidentId] });
      queryClient.invalidateQueries({ queryKey: ["incident-events", incidentId] });
    }
  }, [queryClient]);

  const requestBrowserNotifications = useCallback(async (): Promise<BrowserNotificationPermission> => {
    if (typeof window === "undefined" || !("Notification" in window)) {
      return "unsupported";
    }

    const permission = await Notification.requestPermission();
    setBrowserPermission(permission);
    return permission;
  }, []);

  const refreshBrowserNotificationPermission = useCallback(() => {
    setBrowserPermission(getBrowserNotificationPermission());
  }, []);

  useEffect(() => {
    if (typeof window === "undefined" || !("Notification" in window)) {
      return;
    }

    window.addEventListener("focus", refreshBrowserNotificationPermission);
    document.addEventListener("visibilitychange", refreshBrowserNotificationPermission);

    return () => {
      window.removeEventListener("focus", refreshBrowserNotificationPermission);
      document.removeEventListener("visibilitychange", refreshBrowserNotificationPermission);
    };
  }, [refreshBrowserNotificationPermission]);

  const maybeShowDesktopNotification = useCallback(
    (title: string, body: string, incidentId?: string) => {
      if (typeof window === "undefined" || !window.sentinelDesktop) {
        return false;
      }

      try {
        window.sentinelDesktop.notify({ title, body, incidentId });
        return true;
      } catch {
        return false;
      }
    },
    [],
  );

  const maybeShowBrowserNotification = useCallback(
    (title: string, body: string, tag: string, incidentId?: string) => {
      if (typeof window === "undefined" || !("Notification" in window)) {
        return;
      }
      if (Notification.permission !== "granted") {
        return;
      }
      if (document.visibilityState === "visible" && document.hasFocus()) {
        return;
      }

      if (maybeShowDesktopNotification(title, body, incidentId)) {
        return;
      }

      try {
        const notification = new Notification(title, {
          body,
          tag,
        });
        notification.onclick = () => {
          window.focus();
          if (incidentId) {
            window.location.assign(`/incidents/${encodeURIComponent(incidentId)}`);
          }
          notification.close();
        };
        window.setTimeout(() => notification.close(), 8000);
      } catch {
        // Browser notifications are optional enhancement only.
      }
    },
    [maybeShowDesktopNotification],
  );

  useEffect(() => {
    if (!authReady) {
      return;
    }

    let cancelled = false;

    async function connect() {
      try {
        const res = await fetch(`${API_BASE_URL}/negotiate`);
        if (!res.ok) return;
        const { url, accessToken } = await res.json();

        const connection = new HubConnectionBuilder()
          .withUrl(url, { accessTokenFactory: () => accessToken })
          .withAutomaticReconnect([0, 2000, 5000, 10000, 30000])
          .configureLogging(LogLevel.Warning)
          .build();

        connection.on("incident_created", (payload) => {
          invalidateLiveIncidentViews(payload.incident_id);
          addToast(
            `New incident: ${payload.equipment_id} — ${payload.severity}`,
            "warning",
          );
          maybeShowBrowserNotification(
            `New incident: ${payload.equipment_id}`,
            `${payload.severity} incident requires review.`,
            payload.notification_id ?? payload.incident_id,
            payload.incident_id,
          );
        });

        connection.on("incident_pending_approval", (payload) => {
          invalidateLiveIncidentViews(payload.incident_id);
          addToast(`Incident ready for review: ${payload.equipment_id}`, "info");
          maybeShowBrowserNotification(
            `Decision package ready: ${payload.equipment_id}`,
            payload.title ?? `Incident ${payload.incident_id} is awaiting review.`,
            payload.notification_id ?? payload.incident_id,
            payload.incident_id,
          );
        });

        connection.on("incident_status_changed", (payload) => {
          invalidateLiveIncidentViews(payload.incident_id);
        });

        connection.on("agent_step_completed", (payload) => {
          invalidateLiveIncidentViews(payload.incident_id);
        });

        connection.on("incident_escalated", (payload) => {
          invalidateLiveIncidentViews(payload.incident_id);
          addToast(
            `Incident escalated: ${payload.incident_id}`,
            "error",
          );
          maybeShowBrowserNotification(
            `Incident escalated: ${payload.incident_id}`,
            "QA manager attention required.",
            payload.notification_id ?? payload.incident_id,
            payload.incident_id,
          );
        });

        connection.on("chat_response", (payload) => {
          invalidateLiveIncidentViews(payload.incident_id);
        });

        connection.onreconnected((connectionId) => {
          setConnected(true);
          registeredConnectionIdRef.current = null;
          void registerConnectionGroups(connectionId);
          queryClient.invalidateQueries({ queryKey: ["incidents"] });
          queryClient.invalidateQueries({ queryKey: ["incidents-active-infinite"] });
        });

        connection.onreconnecting(() => setConnected(false));
        connection.onclose(() => {
          registeredConnectionIdRef.current = null;
          if (!cancelled) setConnected(false);
        });

        await connection.start();
        if (!cancelled) {
          connectionRef.current = connection;
          setConnected(true);
        } else {
          await connection.stop();
        }
      } catch {
        // negotiate not available — SignalR disabled gracefully
      }
    }

    connect();
    return () => {
      cancelled = true;
      connectionRef.current?.stop();
    };
  }, [
    authReady,
    queryClient,
    addToast,
    invalidateLiveIncidentViews,
    maybeShowBrowserNotification,
    registerConnectionGroups,
  ]);

  return {
    connected,
    toasts,
    dismissToast,
    browserPermission,
    requestBrowserNotifications,
  };
}
