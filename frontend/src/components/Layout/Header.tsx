import { useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";
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
  onClearAllNotifications?: () => Promise<unknown>;
  onNotificationClick?: (incidentId: string) => Promise<unknown>;
  clearAllNotificationsPending?: boolean;
}

function formatRoleLabel(role: string): string {
  return role
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function getUserInitials(displayName: string): string {
  const parts = displayName
    .split(/\s+/)
    .map((part) => part.trim())
    .filter(Boolean)
    .slice(0, 2);

  if (parts.length === 0) return "SI";
  return parts.map((part) => part.charAt(0).toUpperCase()).join("");
}

function ChevronDownIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M4 6.5 8 10l4-3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function Header({
  onOpenPalette,
  notifications,
  unreadCount,
  notificationsLoading,
  browserNotificationPermission,
  onRequestBrowserNotifications,
  onClearAllNotifications,
  onNotificationClick,
  clearAllNotificationsPending = false,
}: Props) {
  const { displayName, roles, logout } = useAuth();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [notificationDismissVersion, setNotificationDismissVersion] = useState(0);
  const userMenuRef = useRef<HTMLDivElement | null>(null);
  const formattedRoles = useMemo(
    () => roles.map((role) => formatRoleLabel(role)),
    [roles],
  );
  const roleSummary = formattedRoles.join(" • ") || (IS_E2E_AUTH ? "User" : "No app role assigned");
  const userInitials = useMemo(() => getUserInitials(displayName), [displayName]);

  useEffect(() => {
    if (!userMenuOpen) return;

    const handlePointerDown = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setUserMenuOpen(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setUserMenuOpen(false);
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [userMenuOpen]);

  const handleRolePreviewChange = (event: ChangeEvent<HTMLSelectElement>) => {
    setE2EPrimaryRole(event.target.value as AppRole);
    window.location.reload();
  };

  const handleLogout = () => {
    setUserMenuOpen(false);
    logout();
  };

  const handleUserMenuToggle = () => {
    setUserMenuOpen((value) => {
      const nextValue = !value;
      if (nextValue) {
        setNotificationDismissVersion((dismissVersion) => dismissVersion + 1);
      }
      return nextValue;
    });
  };

  const handleNotificationCenterOpen = () => {
    setUserMenuOpen(false);
  };

  return (
    <header className="app-header">
      <Link to="/" className="app-header-brand">
        <img className="app-header-icon" src="/favicon.svg" alt="" aria-hidden="true" />
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
        <div className="user-menu" ref={userMenuRef}>
          <button
            type="button"
            className="user-menu-trigger"
            aria-haspopup="menu"
            aria-expanded={userMenuOpen}
            aria-label={`User menu for ${displayName}`}
            onClick={handleUserMenuToggle}
          >
            <span className="user-avatar" aria-hidden="true">{userInitials}</span>
            <span className="user-menu-text">
              <span className="user-menu-name">{displayName}</span>
            </span>
            <span className="user-menu-chevron" aria-hidden="true">
              <ChevronDownIcon />
            </span>
          </button>

          {userMenuOpen && (
            <div className="user-menu-dropdown" role="menu" aria-label="User menu">
              <div className="user-menu-dropdown-header">
                <div className="user-menu-dropdown-name">{displayName}</div>
                <div className="user-menu-dropdown-meta">
                  {roleSummary}
                </div>
              </div>
              <button type="button" className="user-menu-action" role="menuitem" onClick={handleLogout}>
                Log out
              </button>
            </div>
          )}
        </div>
        <NotificationCenter
          notifications={notifications}
          unreadCount={unreadCount}
          isLoading={notificationsLoading}
          browserNotificationPermission={browserNotificationPermission}
          onRequestBrowserNotifications={onRequestBrowserNotifications}
          onClearAllNotifications={onClearAllNotifications}
          onNotificationClick={onNotificationClick}
          clearAllPending={clearAllNotificationsPending}
          dismissVersion={notificationDismissVersion}
          onOpen={handleNotificationCenterOpen}
        />
      </div>
    </header>
  );
}
