import { useSyncExternalStore } from "react";
import type { AppRole } from "./authRuntime";
import { normalizeRoleClaims } from "./authRuntime";

interface TeamsAuthClaims {
  name?: string;
  preferred_username?: string;
  upn?: string;
  oid?: string;
  sub?: string;
  roles?: unknown;
}

export interface TeamsAuthState {
  isAuthenticated: boolean;
  accessToken: string | null;
  roles: AppRole[];
  displayName: string;
  email: string;
  claims: TeamsAuthClaims | null;
}

const anonymousState: TeamsAuthState = {
  isAuthenticated: false,
  accessToken: null,
  roles: [],
  displayName: "",
  email: "",
  claims: null,
};

let state = anonymousState;
const listeners = new Set<() => void>();

function decodeJwtPayload(token: string): TeamsAuthClaims | null {
  const parts = token.split(".");
  if (parts.length < 2) return null;

  try {
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    return JSON.parse(window.atob(padded)) as TeamsAuthClaims;
  } catch {
    return null;
  }
}

function emit() {
  listeners.forEach((listener) => listener());
}

export function getTeamsAuthState(): TeamsAuthState {
  return state;
}

export function setTeamsAuthToken(accessToken: string): TeamsAuthState {
  const claims = decodeJwtPayload(accessToken);
  state = {
    isAuthenticated: true,
    accessToken,
    roles: normalizeRoleClaims(claims?.roles),
    displayName: claims?.name ?? claims?.preferred_username ?? claims?.upn ?? "Teams user",
    email: claims?.preferred_username ?? claims?.upn ?? "",
    claims,
  };
  emit();
  return state;
}

export function clearTeamsAuthToken(): void {
  state = anonymousState;
  emit();
}

export function useTeamsAuth(): TeamsAuthState {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    getTeamsAuthState,
    getTeamsAuthState,
  );
}