import { useState, useEffect } from "react";
import { Outlet } from "react-router-dom";
import Header from "./Header";
import Sidebar from "./Sidebar";
import AppFooter from "./AppFooter";
import CommandPalette from "./CommandPalette";
import ToastStack from "./ToastStack";
import { useSignalR } from "../../hooks/useSignalR";
import { useAuth } from "../../hooks/useAuth";
import {
  useMarkAllNotificationsRead,
  useMarkIncidentNotificationsRead,
  useNotifications,
  useNotificationSummary,
} from "../../hooks/useNotifications";
import { IS_E2E_AUTH } from "../../authRuntime";

export default function AppShell() {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const { account, rolesHydrated } = useAuth();
  const {
    connected,
    toasts,
    dismissToast,
    browserPermission,
    requestBrowserNotifications,
  } = useSignalR();
  const notificationsEnabled = rolesHydrated && (IS_E2E_AUTH || Boolean(account));
  const { data: notificationFeed, isLoading: notificationsLoading } = useNotifications({
    status: "unread",
    limit: 8,
  }, {
    enabled: notificationsEnabled,
  });
  const { data: notificationSummary } = useNotificationSummary({
    enabled: notificationsEnabled,
  });
  const markAllNotificationsRead = useMarkAllNotificationsRead();
  const markIncidentNotificationsRead = useMarkIncidentNotificationsRead();

  const unreadCount = notificationSummary?.unread_count ?? notificationFeed?.unread_count ?? 0;
  const unreadIncidentIds = notificationSummary?.unread_incident_ids ?? [];

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  return (
    <div className="app-shell">
      <Header
        onOpenPalette={() => setPaletteOpen(true)}
        notifications={notificationFeed?.items ?? []}
        unreadCount={unreadCount}
        notificationsLoading={notificationsLoading}
        browserNotificationPermission={browserPermission}
        onRequestBrowserNotifications={requestBrowserNotifications}
        onClearAllNotifications={() => markAllNotificationsRead.mutateAsync()}
        onNotificationClick={(incidentId) => markIncidentNotificationsRead.mutateAsync(incidentId)}
        clearAllNotificationsPending={markAllNotificationsRead.isPending}
      />
      <div className="app-body">
        <Sidebar unreadIncidentIds={unreadIncidentIds} />
        <main className="app-main">
          <Outlet />
        </main>
      </div>
      <AppFooter connected={connected} />
      <ToastStack toasts={toasts} onDismiss={dismissToast} />
      {paletteOpen && (
        <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
      )}
    </div>
  );
}
