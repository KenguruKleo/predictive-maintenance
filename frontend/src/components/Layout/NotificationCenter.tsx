import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type { BrowserNotificationPermission, NotificationItem } from "../../types/notification";

interface Props {
  notifications: NotificationItem[];
  unreadCount: number;
  isLoading?: boolean;
  browserNotificationPermission: BrowserNotificationPermission;
  onRequestBrowserNotifications?: () => Promise<BrowserNotificationPermission>;
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

export default function NotificationCenter({
  notifications,
  unreadCount,
  isLoading = false,
  browserNotificationPermission,
  onRequestBrowserNotifications,
}: Props) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);

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

  return (
    <div className="notification-center" ref={rootRef}>
      <button
        type="button"
        className="notification-bell"
        aria-label={`Notifications${unreadCount ? `, ${unreadCount} unread` : ""}`}
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="notification-bell-icon" aria-hidden="true">🔔</span>
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
                {unreadCount} item{unreadCount === 1 ? "" : "s"} awaiting review
              </div>
            </div>
            {browserNotificationPermission === "default" && onRequestBrowserNotifications && (
              <button
                type="button"
                className="notification-enable-btn"
                onClick={() => void onRequestBrowserNotifications()}
              >
                Enable browser alerts
              </button>
            )}
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
              notifications.map((notification) => (
                <Link
                  key={notification.id}
                  to={`/incidents/${encodeURIComponent(notification.incident_id)}`}
                  className="notification-item"
                  onClick={() => setOpen(false)}
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
                    {notification.incident_status && <span>{notification.incident_status.replace(/_/g, " ")}</span>}
                  </div>
                  <div className="notification-item-message">{notification.message}</div>
                </Link>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}