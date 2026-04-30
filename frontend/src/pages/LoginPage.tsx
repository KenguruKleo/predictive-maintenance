import { useMsal } from "@azure/msal-react";
import type { AccountInfo, RedirectRequest } from "@azure/msal-browser";
import { useEffect, useState } from "react";
import { popupRedirectUri } from "../authConfig";
import {
  AUTH_POPUP_RESULT_KEY,
  parseAuthPopupResult,
  type AuthPopupResult,
} from "../authPopupBridge";
import { clearTeamsAuthToken, setTeamsAuthToken } from "../teamsAuth";
import {
  authenticateWithTeamsPopup,
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

function openCenteredPopup(url: string): Window | null {
  const width = 520;
  const height = 680;
  const left = Math.max(0, window.screenX + (window.outerWidth - width) / 2);
  const top = Math.max(0, window.screenY + (window.outerHeight - height) / 2);
  return window.open(
    url,
    "sentinel-microsoft-signin",
    `popup=yes,width=${width},height=${height},left=${Math.round(left)},top=${Math.round(top)}`,
  );
}

function isAuthPopupMessage(event: MessageEvent): event is MessageEvent<{
  source: "sentinel-auth-popup";
  nonce: string;
  type: "success" | "error";
  homeAccountId?: string;
  error?: string;
  createdAt: number;
}> {
  return event.origin === window.location.origin
    && event.data?.source === "sentinel-auth-popup";
}

function createNonce(): string {
  return window.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
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
        await handleMicrosoftFallbackLogin();
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

  const handleMicrosoftFallbackLogin = async () => {
    setAuthError(null);
    setIsSigningIn(true);

    try {
      if (isTeamsHost) {
        const nonce = createNonce();
        localStorage.removeItem(AUTH_POPUP_RESULT_KEY);

        const popupUrl = `${popupRedirectUri}?start=1&prompt=select_account&teamsAuth=1&nonce=${encodeURIComponent(nonce)}`;
        const rawResult = await authenticateWithTeamsPopup(popupUrl);
        const result = parseAuthPopupResult(rawResult, nonce)
          ?? parseAuthPopupResult(localStorage.getItem(AUTH_POPUP_RESULT_KEY), nonce);

        if (!result) {
          throw new Error("Microsoft sign-in completed, but Teams did not return a valid auth result.");
        }

        if (result.type === "error") {
          throw new Error(result.error || "Microsoft sign-in failed.");
        }

        const accounts = instance.getAllAccounts();
        const account = accounts.find(
          (candidate) => candidate.homeAccountId === result.homeAccountId,
        ) ?? accounts[0];

        if (!account) {
          throw new Error("Microsoft sign-in completed, but no account was found in the local session.");
        }

        instance.setActiveAccount(account);
        window.location.reload();
        return;
      }

      let completedAccount: AccountInfo | null = null;

      await new Promise<AccountInfo>((resolve, reject) => {
        const nonce = createNonce();
        localStorage.removeItem(AUTH_POPUP_RESULT_KEY);

        const popupUrl = `${popupRedirectUri}?start=1&prompt=select_account&nonce=${encodeURIComponent(nonce)}`;
        const completeFromResult = (result: AuthPopupResult) => {
          if (result.nonce !== nonce) return;

          cleanup();
          popupWindow?.close();

          if (result.type === "error") {
            reject(new Error(result.error || "Microsoft sign-in failed."));
            return;
          }

          const accounts = instance.getAllAccounts();
          const account = accounts.find(
            (candidate) => candidate.homeAccountId === result.homeAccountId,
          ) ?? accounts[0];

          if (!account) {
            reject(new Error("Microsoft sign-in completed, but no account was found in the local session."));
            return;
          }

          instance.setActiveAccount(account);
          completedAccount = account;
          resolve(account);
        };

        let popupWindow: Window | null = null;

        const popup = openCenteredPopup(popupUrl);
        if (!popup) {
          reject(new Error("Microsoft sign-in popup was blocked by the browser."));
          return;
        }
        popupWindow = popup;

        const timeoutId = window.setTimeout(() => {
          cleanup();
          popupWindow?.close();
          reject(new Error("Microsoft sign-in timed out. Close the popup and try again."));
        }, 120_000);

        const resultCheckId = window.setInterval(() => {
          const result = parseAuthPopupResult(localStorage.getItem(AUTH_POPUP_RESULT_KEY), nonce);
          if (result) {
            complete(result);
          }
        }, 500);

        function cleanup() {
          window.clearTimeout(timeoutId);
          window.clearInterval(resultCheckId);
          window.removeEventListener("message", handleMessage);
          window.removeEventListener("storage", handleStorage);
        }

        function complete(result: AuthPopupResult) {
          completeFromResult(result);
        }

        function handleMessage(event: MessageEvent) {
          if (!isAuthPopupMessage(event)) return;
          complete(event.data);
        }

        function handleStorage(event: StorageEvent) {
          if (event.key !== AUTH_POPUP_RESULT_KEY) return;
          const result = parseAuthPopupResult(event.newValue, nonce);
          if (result) {
            complete(result);
          }
        }

        window.addEventListener("message", handleMessage);
        window.addEventListener("storage", handleStorage);
      });

      if (completedAccount && isTeamsHost) {
        window.location.reload();
      }
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : String(error));
    } finally {
      setIsSigningIn(false);
    }
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
              <>
                <button
                  className="login-secondary-button"
                  type="button"
                  onClick={handleMicrosoftFallbackLogin}
                  disabled={isSigningIn}
                >
                  {isTeamsHost ? "Open popup sign-in" : "Sign in with Microsoft account"}
                </button>
                <button className="login-secondary-button" type="button" onClick={handleOpenInBrowser}>
                  Open in browser
                </button>
              </>
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
