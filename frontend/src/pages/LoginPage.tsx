import { useMsal } from "@azure/msal-react";
import type { RedirectRequest } from "@azure/msal-browser";
import "../styles/login.css";

interface LoginPageProps {
  loginRequest: RedirectRequest;
}

export default function LoginPage({ loginRequest }: LoginPageProps) {
  const { instance } = useMsal();

  const handleLogin = () => {
    instance.loginRedirect(loginRequest).catch(console.error);
  };

  return (
    <div className="login-root">
      <div className="login-card">
        <div className="login-logo">
          <span className="login-logo-icon">🛡️</span>
        </div>
        <h1 className="login-title">Sentinel Intelligence</h1>
        <p className="login-subtitle">
          GMP Deviation &amp; CAPA Operations Assistant
        </p>

        <div className="login-divider" />

        <p className="login-description">
          Sign in with your Azure AD account to access the platform.
          Your role determines which incidents and actions are available to you.
        </p>

        <button className="login-button" onClick={handleLogin}>
          <svg className="ms-logo" viewBox="0 0 21 21" xmlns="http://www.w3.org/2000/svg">
            <rect x="1" y="1" width="9" height="9" fill="#f25022" />
            <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
            <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
            <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
          </svg>
          Sign in with Microsoft
        </button>

        <p className="login-roles-note">
          Roles: Operator · QA Manager · Maintenance Tech · Auditor · IT Admin
        </p>
      </div>
    </div>
  );
}
