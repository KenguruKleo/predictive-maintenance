import { useAuth } from "./useAuth";
import type { AppRole } from "./useAuth";

export function useRoleGuard(allowedRoles: AppRole[] | ["*"]) {
  const { roles } = useAuth();
  if (allowedRoles[0] === "*") return true;
  return roles.some((r) => (allowedRoles as AppRole[]).includes(r));
}
