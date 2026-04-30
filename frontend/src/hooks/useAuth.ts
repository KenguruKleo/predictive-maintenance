import { useMsal } from "@azure/msal-react";
import { useEffect, useMemo, useState } from "react";
import { apiRequest } from "../authConfig";
import type { AppRole } from "../authRuntime";
import { clearE2EAuthState, getE2EAuthState, IS_E2E_AUTH } from "../authRuntime";
import { clearTeamsAuthToken, useTeamsAuth } from "../teamsAuth";
import { initializeTeamsRuntime, isLikelyTeamsHost } from "../teamsRuntime";

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
  const teamsAuth = useTeamsAuth();
  const account = accounts[0] ?? null;
  const accountKey = account?.homeAccountId ?? account?.localAccountId ?? account?.username ?? null;
  const e2eAuthState = useMemo(() => getE2EAuthState(), []);
  const [tokenRoleState, setTokenRoleState] = useState<{
    accountKey: string | null;
    roles: AppRole[];
  }>({ accountKey: null, roles: [] });

  useEffect(() => {
    if (IS_E2E_AUTH || !account || !accountKey) {
      return;
    }

    let cancelled = false;

    instance.acquireTokenSilent({
      ...apiRequest,
      account,
    }).then((result) => {
      if (cancelled) return;
      const payload = decodeJwtPayload(result.accessToken);
      setTokenRoleState({ accountKey, roles: normalizeRoles(payload?.roles) });
    }).catch(() => {
      if (!cancelled) {
        setTokenRoleState({ accountKey, roles: [] });
      }
    });

    return () => {
      cancelled = true;
    };
  }, [account, accountKey, instance]);

  const rolesHydrated = teamsAuth.isAuthenticated || IS_E2E_AUTH || !account || tokenRoleState.accountKey === accountKey;

  const roles = useMemo<AppRole[]>(() => {
    if (teamsAuth.isAuthenticated) return teamsAuth.roles;
    if (IS_E2E_AUTH) return e2eAuthState.roles;
    if (!account) return [];
    const accessTokenRoles = tokenRoleState.accountKey === accountKey ? tokenRoleState.roles : [];
    if (accessTokenRoles.length > 0) return accessTokenRoles;

    const claims = account.idTokenClaims as Record<string, unknown> | undefined;
    const normalized = normalizeRoles(claims?.roles);
    return normalized;
  }, [account, accountKey, e2eAuthState.roles, teamsAuth.isAuthenticated, teamsAuth.roles, tokenRoleState.accountKey, tokenRoleState.roles]);

  const displayName = IS_E2E_AUTH
    ? e2eAuthState.displayName
    : teamsAuth.isAuthenticated
      ? teamsAuth.displayName
    : account?.name ?? account?.username ?? "User";
  const email = IS_E2E_AUTH ? e2eAuthState.email : teamsAuth.isAuthenticated ? teamsAuth.email : account?.username ?? "";

  const hasRole = (role: AppRole) => roles.includes(role);
  const hasAnyRole = (...check: AppRole[]) => check.some((r) => roles.includes(r));

  const logout = () => {
    if (IS_E2E_AUTH) {
      clearE2EAuthState();
      window.location.reload();
      return;
    }

    if (teamsAuth.isAuthenticated) {
      clearTeamsAuthToken();
      void instance.clearCache().finally(() => {
        window.location.reload();
      });
      return;
    }

    if (isLikelyTeamsHost()) {
      void initializeTeamsRuntime().then((runtime) => {
        if (runtime.isTeams) {
          clearTeamsAuthToken();
          return instance.clearCache().finally(() => {
            window.location.reload();
          });
        }

        return instance.logoutRedirect({ postLogoutRedirectUri: window.location.origin });
      });
      return;
    }

    instance.logoutRedirect({ postLogoutRedirectUri: window.location.origin });
  };

  return { account, roles, rolesHydrated, displayName, email, hasRole, hasAnyRole, logout };
}
