import { useMsal } from "@azure/msal-react";
import type { RedirectRequest } from "@azure/msal-browser";
import { useEffect, useState } from "react";
import { clearTeamsAuthToken, setTeamsAuthToken } from "../teamsAuth";
import {
  getTeamsAuthErrorMessage,
  getTeamsSsoToken,
  initializeTeamsRuntime,
  isLikelyTeamsHost,
  openAppInBrowser,
} from "../teamsRuntime";
import "../styles/login.css";

interface LoginPageProps {
  loginRequest: RedirectRequest;
}

function isEmbeddedFrame(): boolean {
  try {
    return window.self !== window.top;
  } catch {
    return true;
  }
}

export default function LoginPage({ loginRequest }: LoginPageProps) {
  const { instance } = useMsal();
  const [isTeamsHost, setIsTeamsHost] = useState(() => isLikelyTeamsHost());
  const [isSigningIn, setIsSigningIn] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    if (!isLikelyTeamsHost()) return;

    initializeTeamsRuntime().then((runtime) => {
      if (!cancelled) {
        setIsTeamsHost(runtime.isTeams);
      }
    });

    return () => {
      cancelled = true;
    };
  }, []);

  const handleLogin = async () => {
    setAuthError(null);
    setIsSigningIn(true);

    if (isTeamsHost) {
      try {
        const token = await getTeamsSsoToken();
        const teamsState = setTeamsAuthToken(token);
        if (teamsState.roles.length === 0) {
          clearTeamsAuthToken();
          setAuthError("Teams sign-in succeeded, but this account has no Sentinel app role assigned yet.");
        }
      } catch (error) {
        setAuthError(getTeamsAuthErrorMessage(error));
      } finally {
        setIsSigningIn(false);
      }
      return;
    }

    try {
      if (isEmbeddedFrame()) {
        const result = await instance.loginPopup({ scopes: loginRequest.scopes });
        if (result.account) {
          instance.setActiveAccount(result.account);
        }
      } else {
        await instance.loginRedirect(loginRequest);
      }
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : String(error));
      setIsSigningIn(false);
    }
  };

  const handleOpenInBrowser = () => {
    openAppInBrowser().catch((error) => {
      setAuthError(error instanceof Error ? error.message : String(error));
    });
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
          {isTeamsHost
            ? "Continue with your Microsoft Teams identity to access the platform. Your Sentinel app role determines which incidents and actions are available to you."
            : "Sign in with your Azure AD account to access the platform. Your role determines which incidents and actions are available to you."}
        </p>

        <button className="login-button" onClick={handleLogin} disabled={isSigningIn}>
          <svg className="ms-logo" viewBox="0 0 21 21" xmlns="http://www.w3.org/2000/svg">
            <rect x="1" y="1" width="9" height="9" fill="#f25022" />
            <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
            <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
            <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
          </svg>
          {isSigningIn ? "Signing in…" : isTeamsHost ? "Continue with Teams" : "Sign in with Microsoft"}
        </button>

        {authError && (
          <div className="login-error" role="alert">
            <p>{authError}</p>
            {isTeamsHost && (
              <button className="login-secondary-button" type="button" onClick={handleOpenInBrowser}>
                Open in browser
              </button>
            )}
          </div>
        )}

        <p className="login-roles-note">
          Roles: Operator · QA Manager · Maintenance Tech · Auditor · IT Admin
        </p>
      </div>
    </div>
  );
}
