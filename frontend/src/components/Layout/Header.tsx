import { Link } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { useSignalR } from "../../hooks/useSignalR";

export default function Header() {
  const { displayName, roles, logout } = useAuth();
  const { connected } = useSignalR();

  return (
    <header className="app-header">
      <Link to="/" className="app-header-brand">
        <span className="app-header-icon">🛡️</span>
        <span className="app-header-title">Sentinel Intelligence</span>
      </Link>

      <div className="app-header-right">
        {!connected && (
          <span className="connection-badge disconnected" title="Live updates paused">
            ⚠️ Offline
          </span>
        )}
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
