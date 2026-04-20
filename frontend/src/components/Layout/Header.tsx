import type { ChangeEvent } from "react";
import { Link } from "react-router-dom";
import { APP_ROLE_OPTIONS, IS_E2E_AUTH, setE2EPrimaryRole } from "../../authRuntime";
import type { AppRole } from "../../authRuntime";
import { useAuth } from "../../hooks/useAuth";
import type { BrowserNotificationPermission, NotificationItem } from "../../types/notification";
import NotificationCenter from "./NotificationCenter";

interface Props {
  onOpenPalette?: () => void;
  notifications: NotificationItem[];
  unreadCount: number;
  notificationsLoading?: boolean;
  browserNotificationPermission: BrowserNotificationPermission;
  onRequestBrowserNotifications?: () => Promise<BrowserNotificationPermission>;
}

export default function Header({
  onOpenPalette,
  notifications,
  unreadCount,
  notificationsLoading,
  browserNotificationPermission,
  onRequestBrowserNotifications,
}: Props) {
  const { displayName, roles, logout } = useAuth();

  const handleRolePreviewChange = (event: ChangeEvent<HTMLSelectElement>) => {
    setE2EPrimaryRole(event.target.value as AppRole);
    window.location.reload();
  };

  return (
    <header className="app-header">
      <Link to="/" className="app-header-brand">
        <span className="app-header-icon">🛡️</span>
        <span className="app-header-title">Sentinel Intelligence</span>
      </Link>

      <button className="cp-trigger" onClick={onOpenPalette} title="Quick navigation (⌘K)">
        <span className="cp-trigger-icon">🔍</span>
        <span className="cp-trigger-label">Quick Jump…</span>
        <kbd className="cp-trigger-kbd">⌘K</kbd>
      </button>

      <div className="app-header-right">
        {IS_E2E_AUTH ? (
          <label className="e2e-role-switch">
            <span className="e2e-role-switch-label">Preview role</span>
            <select
              className="e2e-role-switch-select"
              value={roles[0] ?? "operator"}
              onChange={handleRolePreviewChange}
            >
              {APP_ROLE_OPTIONS.map((role) => (
                <option key={role} value={role}>
                  {role}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        <NotificationCenter
          notifications={notifications}
          unreadCount={unreadCount}
          isLoading={notificationsLoading}
          browserNotificationPermission={browserNotificationPermission}
          onRequestBrowserNotifications={onRequestBrowserNotifications}
        />
        <span className="user-name">{displayName}</span>
        {roles.map((role) => (
          <span key={role} className="role-badge">
            {role}
          </span>
        ))}
        <button className="logout-btn" onClick={logout}>
          Sign Out
        </button>
      </div>
    </header>
  );
}
