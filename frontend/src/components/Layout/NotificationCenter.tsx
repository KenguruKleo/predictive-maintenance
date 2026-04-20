import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type { BrowserNotificationPermission, NotificationItem } from "../../types/notification";
import StatusBadge from "../IncidentList/StatusBadge";

interface Props {
  notifications: NotificationItem[];
  unreadCount: number;
  isLoading?: boolean;
  browserNotificationPermission: BrowserNotificationPermission;
  onRequestBrowserNotifications?: () => Promise<BrowserNotificationPermission>;
  onClearAllNotifications?: () => Promise<unknown>;
  onNotificationClick?: (incidentId: string) => Promise<unknown>;
  clearAllPending?: boolean;
  dismissVersion?: number;
  onOpen?: () => void;
}

type NotificationPresentationKind = "actionable" | "informational";

function BellIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path
        d="M10 3.25a3 3 0 0 0-3 3v1.12c0 .78-.23 1.53-.66 2.18L5.2 11.25c-.56.85-.15 2 .83 2h7.94c.98 0 1.39-1.15.83-2l-1.14-1.7A3.93 3.93 0 0 1 13 7.37V6.25a3 3 0 0 0-3-3Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M8.4 15.25a1.9 1.9 0 0 0 3.2 0" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function formatNotificationDate(value?: string): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function getPresentationKind(notification: NotificationItem): NotificationPresentationKind {
  if (notification.presentation_kind === "actionable" || notification.presentation_kind === "informational") {
    return notification.presentation_kind;
  }

  return notification.incident_status === "awaiting_agents" ? "informational" : "actionable";
}

function buildNotificationSubtitle(notifications: NotificationItem[], unreadCount: number): string {
  if (unreadCount === 0) {
    return "No active notifications";
  }

  const actionableCount = notifications.filter((notification) => getPresentationKind(notification) === "actionable").length;
  const informationalCount = notifications.length - actionableCount;
  const parts: string[] = [];

  if (actionableCount > 0) {
    parts.push(`${actionableCount} decision${actionableCount === 1 ? "" : "s"} pending`);
  }
  if (informationalCount > 0) {
    parts.push(`${informationalCount} update${informationalCount === 1 ? "" : "s"}`);
  }

  const summary = parts.join(", ") || `${unreadCount} active notification${unreadCount === 1 ? "" : "s"}`;
  if (notifications.length < unreadCount && notifications.length > 0) {
    return `Latest ${notifications.length} of ${unreadCount}: ${summary}`;
  }
  return summary;
}

export default function NotificationCenter({
  notifications,
  unreadCount,
  isLoading = false,
  browserNotificationPermission,
  onRequestBrowserNotifications,
  onClearAllNotifications,
  onNotificationClick,
  clearAllPending = false,
  dismissVersion = 0,
  onOpen,
}: Props) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setOpen(false);
  }, [dismissVersion]);

  useEffect(() => {
    if (!open) return;

    const handlePointerDown = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open]);

  const unreadLabel = useMemo(() => (unreadCount > 9 ? "9+" : String(unreadCount)), [unreadCount]);
  const subtitle = useMemo(
    () => buildNotificationSubtitle(notifications, unreadCount),
    [notifications, unreadCount],
  );

  const handleBellClick = () => {
    setOpen((value) => {
      const nextValue = !value;
      if (nextValue) {
        onOpen?.();
      }
      return nextValue;
    });
  };

  const handleNotificationClick = (incidentId: string) => {
    setOpen(false);
    void onNotificationClick?.(incidentId);
  };

  return (
    <div className="notification-center" ref={rootRef}>
      <button
        type="button"
        className="notification-bell"
        aria-label={`Notifications${unreadCount ? `, ${unreadCount} unread` : ""}`}
        aria-expanded={open}
        onClick={handleBellClick}
      >
        <span className="notification-bell-icon" aria-hidden="true">
          <BellIcon />
        </span>
        {unreadCount > 0 && (
          <span className="notification-bell-badge">{unreadLabel}</span>
        )}
      </button>

      {open && (
        <div className="notification-dropdown" role="dialog" aria-label="Unread notifications">
          <div className="notification-dropdown-header">
            <div>
              <div className="notification-dropdown-title">Unread notifications</div>
              <div className="notification-dropdown-subtitle">
                {subtitle}
              </div>
            </div>
            <div className="notification-dropdown-actions">
              {browserNotificationPermission === "default" && onRequestBrowserNotifications && (
                <button
                  type="button"
                  className="notification-enable-btn"
                  onClick={() => void onRequestBrowserNotifications()}
                >
                  Enable browser alerts
                </button>
              )}
              {onClearAllNotifications && unreadCount > 0 && (
                <button
                  type="button"
                  className="notification-clear-btn"
                  onClick={() => void onClearAllNotifications()}
                  disabled={clearAllPending}
                >
                  {clearAllPending ? "Clearing…" : "Clear all"}
                </button>
              )}
            </div>
          </div>

          {browserNotificationPermission === "denied" && (
            <div className="notification-browser-status">
              Browser alerts are blocked for this site. In-app notifications remain active.
            </div>
          )}

          {browserNotificationPermission === "unsupported" && (
            <div className="notification-browser-status">
              Browser alerts are unavailable in this environment. In-app notifications remain active.
            </div>
          )}

          <div className="notification-dropdown-list">
            {isLoading && notifications.length === 0 ? (
              <div className="notification-empty">Loading notifications…</div>
            ) : notifications.length === 0 ? (
              <div className="notification-empty">No unread notifications.</div>
            ) : (
              notifications.map((notification) => {
                const presentationKind = getPresentationKind(notification);
                return (
                <Link
                  key={notification.id}
                  to={`/incidents/${encodeURIComponent(notification.incident_id)}`}
                  className={`notification-item notification-item--${presentationKind}`}
                  onClick={() => handleNotificationClick(notification.incident_id)}
                >
                  <div className="notification-item-header">
                    <span className="notification-item-title">
                      {notification.title || notification.equipment_id || notification.incident_id}
                    </span>
                    <span className="notification-item-date">
                      {formatNotificationDate(notification.created_at)}
                    </span>
                  </div>
                  <div className="notification-item-meta">
                    <span>{notification.incident_id}</span>
                    {notification.equipment_id && <span>{notification.equipment_id}</span>}
                  </div>
                  {notification.incident_status && (
                    <div className="notification-item-status-row">
                      <StatusBadge status={notification.incident_status} />
                    </div>
                  )}
                  <div className="notification-item-message">{notification.message}</div>
                </Link>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}