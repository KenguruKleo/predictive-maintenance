import { NavLink } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { useIncidents } from "../../hooks/useIncidents";
import ActiveIncidentItem from "./ActiveIncidentItem";

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

  const { data: activeData } = useIncidents({
    status: [
      "ingested",
      "analyzing",
      "pending_approval",
      "escalated",
      "approved",
    ],
    page_size: 50,
  });

  const hasRole = (itemRoles: readonly string[]) => {
    if (itemRoles[0] === "*") return true;
    return roles.some((r) => (itemRoles as readonly string[]).includes(r));
  };

  const activeIncidents = activeData?.items ?? [];

  return (
    <aside className="sidebar">
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
          Active Incidents ({activeIncidents.length})
        </div>
        {activeIncidents.length === 0 && (
          <div className="sidebar-empty">No active incidents</div>
        )}
        {activeIncidents.map((inc) => (
          <ActiveIncidentItem key={inc.id} incident={inc} />
        ))}
      </div>
    </aside>
  );
}

