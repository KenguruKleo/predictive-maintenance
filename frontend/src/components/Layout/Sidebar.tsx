import { useCallback, useEffect, useRef, useState } from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { useInfiniteActiveIncidents } from "../../hooks/useIncidents";
import ActiveIncidentItem from "./ActiveIncidentItem";

const MIN_WIDTH = 180;
const MAX_WIDTH = 420;
const DEFAULT_WIDTH = 240;

type NavIconProps = React.SVGProps<SVGSVGElement>;

function OperationsIcon(props: NavIconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <rect x="4" y="4" width="16" height="16" rx="2.5" />
      <path d="M9 8.5h6" />
      <path d="M9 12h6" />
      <path d="M9 15.5h4" />
      <circle cx="7" cy="8.5" r="0.85" fill="currentColor" stroke="none" />
      <circle cx="7" cy="12" r="0.85" fill="currentColor" stroke="none" />
      <circle cx="7" cy="15.5" r="0.85" fill="currentColor" stroke="none" />
    </svg>
  );
}

function HistoryAuditIcon(props: NavIconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M4 9V7a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2Z" />
      <path d="M4 9h16" />
      <path d="M8.5 13h7" />
      <path d="M8.5 16.5h4.5" />
    </svg>
  );
}

function ManagerDashboardIcon(props: NavIconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <rect x="4" y="4" width="16" height="16" rx="2.5" />
      <path d="M8 15.5V11" />
      <path d="M12 15.5V8" />
      <path d="M16 15.5V13" />
      <path d="M7 18h10" />
    </svg>
  );
}

function TelemetryIcon(props: NavIconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M5 15a7 7 0 0 1 14 0" />
      <path d="M12 15l3.5-3.5" />
      <path d="M8 18.5h8" />
      <circle cx="12" cy="15" r="1.25" fill="currentColor" stroke="none" />
    </svg>
  );
}

function TemplatesIcon(props: NavIconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M8 4.5h6l3 3V19a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V6.5a2 2 0 0 1 2-2Z" />
      <path d="M14 4.5v4h4" />
      <path d="M9 11h6" />
      <path d="M9 14.5h6" />
      <path d="M9 18h4" />
    </svg>
  );
}

function useSidebarResize() {
  const [width, setWidth] = useState<number>(() => {
    const saved = localStorage.getItem("sidebar-width");
    return saved ? parseInt(saved, 10) : DEFAULT_WIDTH;
  });
  const [dragging, setDragging] = useState(false);
  const startX = useRef(0);
  const startW = useRef(0);

  useEffect(() => {
    document.documentElement.style.setProperty("--sidebar-width", `${width}px`);
    localStorage.setItem("sidebar-width", String(width));
  }, [width]);

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    startX.current = e.clientX;
    startW.current = width;
    setDragging(true);
  }, [width]);

  useEffect(() => {
    if (!dragging) return;
    const onMove = (e: MouseEvent) => {
      const delta = e.clientX - startX.current;
      const next = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, startW.current + delta));
      setWidth(next);
    };
    const onUp = () => setDragging(false);
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
    return () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
  }, [dragging]);

  return { dragging, onMouseDown };
}

const NAV_GROUPS = [
  {
    label: "MONITORING",
    items: [
      {
        to: "/",
        label: "Operations",
        icon: OperationsIcon,
        roles: ["operator", "qa-manager", "it-admin"],
      },
      {
        to: "/history",
        label: "History & Audit",
        icon: HistoryAuditIcon,
        roles: ["*"],
      },
    ],
  },
  {
    label: "MANAGEMENT",
    items: [
      {
        to: "/manager",
        label: "Manager Dashboard",
        icon: ManagerDashboardIcon,
        roles: ["qa-manager", "it-admin"],
      },
      {
        to: "/telemetry",
        label: "Telemetry",
        icon: TelemetryIcon,
        roles: ["qa-manager", "auditor", "it-admin"],
      },
      {
        to: "/templates",
        label: "Templates",
        icon: TemplatesIcon,
        roles: ["it-admin"],
      },
    ],
  },
] as const;

interface Props {
  unreadIncidentIds?: string[];
}

export default function Sidebar({ unreadIncidentIds = [] }: Props) {
  const { roles } = useAuth();
  const { dragging, onMouseDown } = useSidebarResize();

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteActiveIncidents(20);

  // flatten all pages
  const activeIncidents = data?.pages.flatMap((p) => p.items) ?? [];
  const total = data?.pages[0]?.total ?? 0;

  // sentinel element for infinite scroll
  const sentinelRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      },
      { threshold: 0.1 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [fetchNextPage, hasNextPage, isFetchingNextPage]);

  const hasRole = (itemRoles: readonly string[]) => {
    if (itemRoles[0] === "*") return true;
    return roles.some((r) => (itemRoles as readonly string[]).includes(r));
  };

  return (
    <aside className="sidebar">
      <div
        className={`sidebar-resize-handle${dragging ? " dragging" : ""}`}
        onMouseDown={onMouseDown}
        title="Drag to resize"
      />
      <nav className="sidebar-nav">
        {NAV_GROUPS.map((group) => {
          const visibleItems = group.items.filter((item) => hasRole(item.roles));
          if (!visibleItems.length) return null;
          return (
            <div key={group.label} className="sidebar-nav-group">
              <div className="sidebar-nav-group-label">{group.label}</div>
              {visibleItems.map((item) => {
                const Icon = item.icon;

                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === "/"}
                    className={({ isActive }) =>
                      `sidebar-nav-item ${isActive ? "active" : ""}`
                    }
                  >
                    <span className="sidebar-nav-icon" aria-hidden="true">
                      <Icon aria-hidden="true" focusable="false" />
                    </span>
                    <span className="sidebar-nav-label">{item.label}</span>
                  </NavLink>
                );
              })}
            </div>
          );
        })}
      </nav>

      <div className="sidebar-divider" />

      <div className="sidebar-active-incidents">
        <div className="sidebar-section-title">
          Active Incidents ({total > 0 ? total : activeIncidents.length})
        </div>
        {activeIncidents.length === 0 && (
          <div className="sidebar-empty">No active incidents</div>
        )}
        {activeIncidents.map((inc) => (
          <ActiveIncidentItem
            key={inc.id}
            incident={inc}
            isUnread={unreadIncidentIds.includes(inc.id)}
          />
        ))}
        {/* Infinite scroll sentinel */}
        <div ref={sentinelRef} style={{ height: 1 }} />
        {isFetchingNextPage && (
          <div className="sidebar-loading">Loading…</div>
        )}
      </div>
    </aside>
  );
}

