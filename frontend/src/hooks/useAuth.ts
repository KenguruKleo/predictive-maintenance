import { useMsal } from "@azure/msal-react";
import { useMemo } from "react";

export type AppRole =
  | "operator"
  | "qa-manager"
  | "maintenance-tech"
  | "auditor"
  | "it-admin";

export function useAuth() {
  const { instance, accounts } = useMsal();
  const account = accounts[0] ?? null;

  const roles = useMemo<AppRole[]>(() => {
    if (!account) return [];
    const claims = account.idTokenClaims as Record<string, unknown> | undefined;
    const raw = claims?.roles;
    if (Array.isArray(raw)) return raw as AppRole[];
    return [];
  }, [account]);

  const displayName = account?.name ?? account?.username ?? "User";
  const email = account?.username ?? "";

  const hasRole = (role: AppRole) => roles.includes(role);
  const hasAnyRole = (...check: AppRole[]) => check.some((r) => roles.includes(r));

  const logout = () => {
    instance.logoutRedirect({ postLogoutRedirectUri: window.location.origin });
  };

  return { account, roles, displayName, email, hasRole, hasAnyRole, logout };
}
