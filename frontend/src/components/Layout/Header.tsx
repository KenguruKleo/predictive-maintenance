import { Link } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";

interface Props {
  onOpenPalette?: () => void;
}

export default function Header({ onOpenPalette }: Props) {
  const { displayName, roles, logout } = useAuth();

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
