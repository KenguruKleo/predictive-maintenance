import { useState, useEffect } from "react";
import { useIsAuthenticated, useMsal } from "@azure/msal-react";
import { apiRequest } from "../../authConfig";

/** Decode JWT payload without verification (display only — trust comes from server-side). */
function parseJwtRoles(token: string): string[] {
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return Array.isArray(payload.roles) ? payload.roles : [];
  } catch {
    return [];
  }
}

/**
 * AppShell — shows authenticated user info.
 * Roles are read from the API access token (not ID token) because
 * app roles are assigned on the API service principal.
 */
export default function AppShell() {
  const { instance } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const account = instance.getActiveAccount();
  const [roles, setRoles] = useState<string[]>([]);

  useEffect(() => {
    if (!account) return;
    instance
      .acquireTokenSilent({ ...apiRequest, account })
      .then((res) => setRoles(parseJwtRoles(res.accessToken)))
      .catch(() => {
        // Fallback: try roles from ID token claims (may be empty)
        const idRoles = (account.idTokenClaims as Record<string, unknown>)?.roles;
        setRoles(Array.isArray(idRoles) ? idRoles : []);
      });
  }, [account, instance]);

  const handleLogout = () => {
    instance.logoutRedirect({ postLogoutRedirectUri: window.location.origin });
  };

  if (!isAuthenticated || !account) return null;

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-brand">
          <span className="app-header-icon">🛡️</span>
          <span className="app-header-title">Sentinel Intelligence</span>
        </div>
        <div className="app-header-user">
          <span className="user-name">{account.name}</span>
          {roles.map((r) => (
            <span key={r} className={`role-badge role-badge--${r.toLowerCase()}`}>
              {r}
            </span>
          ))}
          <button className="logout-btn" onClick={handleLogout}>
            Sign out
          </button>
        </div>
      </header>

      <main className="app-main">
        <div className="welcome-card">
          <h2>Welcome, {account.name?.split(" ")[0]}!</h2>
          <p>Authentication successful. Incidents dashboard coming next.</p>

          <div className="auth-info">
            <h3>Your session</h3>
            <table>
              <tbody>
                <tr><td>User</td><td>{account.username}</td></tr>
                <tr><td>Tenant</td><td>{account.tenantId}</td></tr>
                <tr>
                  <td>Roles</td>
                  <td>
                    {roles.length > 0
                      ? roles.join(", ")
                      : <span className="no-roles">No app roles assigned</span>}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}
