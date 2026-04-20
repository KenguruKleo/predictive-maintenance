import { useMsal } from "@azure/msal-react";
import { useEffect, useMemo, useState } from "react";
import { apiRequest } from "../authConfig";
import type { AppRole } from "../authRuntime";
import { clearE2EAuthState, getE2EAuthState, IS_E2E_AUTH } from "../authRuntime";

export type { AppRole } from "../authRuntime";

function normalizeRole(value: unknown): AppRole | null {
  if (typeof value !== "string") return null;
  const normalized = value.trim();
  if (!normalized) return null;
  if (normalized === "Operator" || normalized === "operator") return "operator";
  if (normalized === "QAManager" || normalized === "qamanager" || normalized === "QA Manager" || normalized === "qa-manager") return "qa-manager";
  if (normalized === "MaintenanceTech" || normalized === "maintenancetech" || normalized === "Maintenance Technician" || normalized === "maintenance-tech") return "maintenance-tech";
  if (normalized === "Auditor" || normalized === "auditor") return "auditor";
  if (normalized === "ITAdmin" || normalized === "itadmin" || normalized === "IT Administrator" || normalized === "it-admin") return "it-admin";
  return null;
}

function normalizeRoles(raw: unknown): AppRole[] {
  const values = Array.isArray(raw) ? raw : [raw];
  const normalized = values
    .map((role) => normalizeRole(role))
    .filter((role): role is AppRole => Boolean(role));
  return normalized.length > 0 ? Array.from(new Set(normalized)) : [];
}

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  const parts = token.split(".");
  if (parts.length < 2) return null;

  try {
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    return JSON.parse(window.atob(padded)) as Record<string, unknown>;
  } catch {
    return null;
  }
}

export function useAuth() {
  const { instance, accounts } = useMsal();
  const account = accounts[0] ?? null;
  const e2eAuthState = useMemo(() => getE2EAuthState(), []);
  const [accessTokenRoles, setAccessTokenRoles] = useState<AppRole[]>([]);
  const [rolesHydrated, setRolesHydrated] = useState(IS_E2E_AUTH);

  useEffect(() => {
    if (IS_E2E_AUTH || !account) {
      setAccessTokenRoles([]);
      setRolesHydrated(true);
      return;
    }

    let cancelled = false;
    setRolesHydrated(false);

    instance.acquireTokenSilent({
      ...apiRequest,
      account,
    }).then((result) => {
      if (cancelled) return;
      const payload = decodeJwtPayload(result.accessToken);
      setAccessTokenRoles(normalizeRoles(payload?.roles));
      setRolesHydrated(true);
    }).catch(() => {
      if (!cancelled) {
        setAccessTokenRoles([]);
        setRolesHydrated(true);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [account, instance]);

  const roles = useMemo<AppRole[]>(() => {
    if (IS_E2E_AUTH) return e2eAuthState.roles;
    if (!account) return [];
    if (accessTokenRoles.length > 0) return accessTokenRoles;

    const claims = account.idTokenClaims as Record<string, unknown> | undefined;
    const normalized = normalizeRoles(claims?.roles);
    return normalized;
  }, [account, accessTokenRoles, e2eAuthState.roles]);

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

  return { account, roles, rolesHydrated, displayName, email, hasRole, hasAnyRole, logout };
}
