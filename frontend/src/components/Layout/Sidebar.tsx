import { useCallback, useEffect, useRef, useState } from "react";
import { NavLink } from "react-router-dom";
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
        icon: "📋",
        roles: ["operator", "qa-manager", "it-admin"],
      },
      {
        to: "/history",
        label: "History & Audit",
        icon: "📂",
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
        icon: "📊",
        roles: ["qa-manager", "it-admin"],
      },
      {
        to: "/templates",
        label: "Templates",
        icon: "📄",
        roles: ["it-admin"],
      },
    ],
  },
] as const;

export default function Sidebar() {
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
              {visibleItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/"}
                  className={({ isActive }) =>
                    `sidebar-nav-item ${isActive ? "active" : ""}`
                  }
                >
                  <span className="sidebar-nav-icon">{item.icon}</span>
                  {item.label}
                </NavLink>
              ))}
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
          <ActiveIncidentItem key={inc.id} incident={inc} />
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

