import { useMsal } from "@azure/msal-react";
import { useMemo } from "react";

export type AppRole =
  | "operator"
  | "qa-manager"
  | "maintenance-tech"
  | "auditor"
  | "it-admin";

const ROLE_MAP: Record<string, AppRole> = {
  operator: "operator",
  Operator: "operator",
  qamanager: "qa-manager",
  QAManager: "qa-manager",
  "QA Manager": "qa-manager",
  "qa-manager": "qa-manager",
  MaintenanceTech: "maintenance-tech",
  maintenancetech: "maintenance-tech",
  "Maintenance Technician": "maintenance-tech",
  "maintenance-tech": "maintenance-tech",
  Auditor: "auditor",
  auditor: "auditor",
  ITAdmin: "it-admin",
  "IT Administrator": "it-admin",
  itadmin: "it-admin",
  "it-admin": "it-admin",
};

export function useAuth() {
  const { instance, accounts } = useMsal();
  const account = accounts[0] ?? null;

  const roles = useMemo<AppRole[]>(() => {
    if (!account) return [];
    const claims = account.idTokenClaims as Record<string, unknown> | undefined;
    const raw = claims?.roles;
    if (!Array.isArray(raw)) return ["operator"];
    const normalized = raw
      .map((role) => ROLE_MAP[String(role)] ?? ROLE_MAP[String(role).toLowerCase()])
      .filter((role): role is AppRole => Boolean(role));
    return normalized.length > 0 ? Array.from(new Set(normalized)) : ["operator"];
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
