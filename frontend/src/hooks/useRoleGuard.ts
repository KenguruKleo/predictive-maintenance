import { useAuth } from "./useAuth";
import type { AppRole } from "../authRuntime";

export function useRoleGuard(allowedRoles: AppRole[] | ["*"]) {
  const { roles, rolesHydrated } = useAuth();

  if (allowedRoles[0] === "*") {
    return { allowed: true, pending: false };
  }

  if (!rolesHydrated) {
    return { allowed: false, pending: true };
  }

  return {
    allowed: roles.some((role) => (allowedRoles as AppRole[]).includes(role)),
    pending: false,
  };
}
