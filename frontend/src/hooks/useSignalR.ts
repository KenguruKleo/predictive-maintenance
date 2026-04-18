import { useEffect, useRef, useState, useCallback } from "react";
import {
  HubConnection,
  HubConnectionBuilder,
  LogLevel,
} from "@microsoft/signalr";
import { useQueryClient } from "@tanstack/react-query";
import { API_BASE_URL } from "../authConfig";

export interface Toast {
  id: string;
  message: string;
  type: "info" | "warning" | "success" | "error";
  timestamp: number;
}

export function useSignalR() {
  const connectionRef = useRef<HubConnection | null>(null);
  const [connected, setConnected] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const queryClient = useQueryClient();

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

  const invalidateLiveIncidentViews = useCallback((incidentId?: string) => {
    queryClient.invalidateQueries({ queryKey: ["incidents"] });
    queryClient.invalidateQueries({ queryKey: ["incidents-active-infinite"] });
    if (incidentId) {
      queryClient.invalidateQueries({ queryKey: ["incident", incidentId] });
      queryClient.invalidateQueries({ queryKey: ["incident-events", incidentId] });
    }
  }, [queryClient]);

  useEffect(() => {
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
        });

        connection.on("incident_pending_approval", (payload) => {
          invalidateLiveIncidentViews(payload.incident_id);
          addToast(`Incident ready for review: ${payload.equipment_id}`, "info");
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
        });

        connection.on("chat_response", (payload) => {
          invalidateLiveIncidentViews(payload.incident_id);
        });

        connection.onreconnected(() => {
          setConnected(true);
          queryClient.invalidateQueries({ queryKey: ["incidents"] });
          queryClient.invalidateQueries({ queryKey: ["incidents-active-infinite"] });
        });

        connection.onreconnecting(() => setConnected(false));
        connection.onclose(() => {
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
  }, [queryClient, addToast, invalidateLiveIncidentViews]);

  return { connected, toasts, dismissToast };
}
