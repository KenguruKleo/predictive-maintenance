import { useMsal } from "@azure/msal-react";
import { useMemo } from "react";
import type { AppRole } from "../authRuntime";
import { clearE2EAuthState, getE2EAuthState, IS_E2E_AUTH } from "../authRuntime";

export type { AppRole } from "../authRuntime";

export function useAuth() {
  const { instance, accounts } = useMsal();
  const account = accounts[0] ?? null;
  const e2eAuthState = useMemo(() => getE2EAuthState(), []);

  const roles = useMemo<AppRole[]>(() => {
    if (IS_E2E_AUTH) return e2eAuthState.roles;
    if (!account) return [];
    const claims = account.idTokenClaims as Record<string, unknown> | undefined;
    const raw = claims?.roles;
    if (!Array.isArray(raw)) return ["operator"];
    const normalized = raw
      .map((role) => {
        const value = String(role);
        if (value === "Operator" || value === "operator") return "operator";
        if (value === "QAManager" || value === "qamanager" || value === "QA Manager" || value === "qa-manager") return "qa-manager";
        if (value === "MaintenanceTech" || value === "maintenancetech" || value === "Maintenance Technician" || value === "maintenance-tech") return "maintenance-tech";
        if (value === "Auditor" || value === "auditor") return "auditor";
        if (value === "ITAdmin" || value === "itadmin" || value === "IT Administrator" || value === "it-admin") return "it-admin";
        return null;
      })
      .filter((role): role is AppRole => Boolean(role));
    return normalized.length > 0 ? Array.from(new Set(normalized)) : ["operator"];
  }, [account, e2eAuthState.roles]);

  const displayName = IS_E2E_AUTH
    ? e2eAuthState.displayName
    : account?.name ?? account?.username ?? "User";
  const email = IS_E2E_AUTH ? e2eAuthState.email : account?.username ?? "";

  const hasRole = (role: AppRole) => roles.includes(role);
  const hasAnyRole = (...check: AppRole[]) => check.some((r) => roles.includes(r));

  const logout = () => {
    if (IS_E2E_AUTH) {
      clearE2EAuthState();
      window.location.reload();
      return;
    }
    instance.logoutRedirect({ postLogoutRedirectUri: window.location.origin });
  };

  return { account, roles, displayName, email, hasRole, hasAnyRole, logout };
}
