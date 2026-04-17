import { NavLink } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { useIncidents } from "../../hooks/useIncidents";
import ActiveIncidentItem from "./ActiveIncidentItem";

const NAV_ITEMS = [
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

  const visibleNav = NAV_ITEMS.filter((item) => {
    if (item.roles[0] === "*") return true;
    return roles.some((r) => (item.roles as readonly string[]).includes(r));
  });

  const activeIncidents = activeData?.items ?? [];

  return (
    <aside className="sidebar">
      <nav className="sidebar-nav">
        {visibleNav.map((item) => (
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
