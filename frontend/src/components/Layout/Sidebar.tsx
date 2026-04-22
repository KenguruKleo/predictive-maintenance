import { useCallback, useEffect, useRef, useState } from "react";
import { NavLink } from "react-router-dom";
import {
  Layers,
  FolderClock,
  LayoutDashboard,
  Gauge,
  FileStack,
} from "lucide-react";
import { useAuth } from "../../hooks/useAuth";
import { useInfiniteActiveIncidents } from "../../hooks/useIncidents";
import ActiveIncidentItem from "./ActiveIncidentItem";

const MIN_WIDTH = 180;
const MAX_WIDTH = 420;
const DEFAULT_WIDTH = 240;

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
        icon: Layers,
        roles: ["operator", "qa-manager", "it-admin"],
      },
      {
        to: "/history",
        label: "History & Audit",
        icon: FolderClock,
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
        icon: LayoutDashboard,
        roles: ["qa-manager", "it-admin"],
      },
      {
        to: "/telemetry",
        label: "Telemetry",
        icon: Gauge,
        roles: ["qa-manager", "auditor", "it-admin"],
      },
      {
        to: "/templates",
        label: "Templates",
        icon: FileStack,
        roles: ["it-admin"],
      },
    ],
  },
] as const;

interface Props {
  unreadIncidentIds?: string[];
  onIncidentAcknowledge?: (incidentId: string) => Promise<unknown>;
}

export default function Sidebar({ unreadIncidentIds = [], onIncidentAcknowledge }: Props) {
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
            onAcknowledge={onIncidentAcknowledge}
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

