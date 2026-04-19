export type AuthMode = "msal" | "e2e";

export type AppRole =
  | "operator"
  | "qa-manager"
  | "maintenance-tech"
  | "auditor"
  | "it-admin";

export interface E2EAuthState {
  userId: string;
  displayName: string;
  email: string;
  roles: AppRole[];
}

const STORAGE_KEY = "sentinel:e2e-auth";

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

const MOCK_ROLE_CLAIMS: Record<AppRole, string> = {
  operator: "Operator",
  "qa-manager": "QAManager",
  "maintenance-tech": "MaintenanceTech",
  auditor: "Auditor",
  "it-admin": "ITAdmin",
};

const RAW_AUTH_MODE = String(import.meta.env.VITE_AUTH_MODE ?? "msal").toLowerCase();

export const AUTH_MODE: AuthMode = RAW_AUTH_MODE === "e2e" ? "e2e" : "msal";
export const IS_E2E_AUTH = AUTH_MODE === "e2e";

function normalizeRole(value: unknown): AppRole | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  return ROLE_MAP[trimmed] ?? ROLE_MAP[trimmed.toLowerCase()] ?? null;
}

function normalizeRoles(value: unknown): AppRole[] {
  const rawRoles = Array.isArray(value) ? value : [value];
  const normalized = rawRoles
    .map((role) => normalizeRole(role))
    .filter((role): role is AppRole => Boolean(role));
  return normalized.length > 0 ? Array.from(new Set(normalized)) : ["operator"];
}

function getDefaultAuthState(): E2EAuthState {
  const defaultRole = normalizeRole(import.meta.env.VITE_E2E_DEFAULT_ROLE) ?? "operator";
  const userId = String(import.meta.env.VITE_E2E_DEFAULT_USER_ID ?? "ivan.petrenko");
  const displayName = String(import.meta.env.VITE_E2E_DEFAULT_NAME ?? "Ivan Petrenko");
  const email = String(
    import.meta.env.VITE_E2E_DEFAULT_EMAIL ?? `${userId}@local.test`,
  );

  return {
    userId,
    displayName,
    email,
    roles: [defaultRole],
  };
}

function getStoredAuthState(): Partial<E2EAuthState> | null {
  if (typeof window === "undefined") return null;

  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;

  try {
    return JSON.parse(raw) as Partial<E2EAuthState>;
  } catch {
    return null;
  }
}

export function getE2EAuthState(): E2EAuthState {
  const defaults = getDefaultAuthState();
  const stored = getStoredAuthState();

  if (!stored) return defaults;

  const userId = typeof stored.userId === "string" && stored.userId.trim()
    ? stored.userId.trim()
    : defaults.userId;
  const displayName = typeof stored.displayName === "string" && stored.displayName.trim()
    ? stored.displayName.trim()
    : defaults.displayName;
  const email = typeof stored.email === "string" && stored.email.trim()
    ? stored.email.trim()
    : defaults.email;

  return {
    userId,
    displayName,
    email,
    roles: normalizeRoles(stored.roles),
  };
}

export function clearE2EAuthState(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}

export function getE2ERequestHeaders(): Record<string, string> {
  const authState = getE2EAuthState();
  return {
    "X-Mock-Role": authState.roles.map((role) => MOCK_ROLE_CLAIMS[role]).join(","),
    "X-Mock-User": authState.userId,
  };
}

export function getE2EDecisionDefaults(): { userId: string; role: AppRole } {
  const authState = getE2EAuthState();
  return {
    userId: authState.userId,
    role: authState.roles[0] ?? "operator",
  };
}
