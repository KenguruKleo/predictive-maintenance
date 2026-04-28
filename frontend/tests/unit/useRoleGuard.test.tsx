import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useRoleGuard } from "../../src/hooks/useRoleGuard";

const mockUseAuth = vi.fn();

vi.mock("../../src/hooks/useAuth", () => ({
  useAuth: () => mockUseAuth(),
}));

describe("useRoleGuard", () => {
  beforeEach(() => {
    mockUseAuth.mockReset();
  });

  it("allows wildcard access immediately", () => {
    mockUseAuth.mockReturnValue({ roles: [], rolesHydrated: false });

    const { result } = renderHook(() => useRoleGuard(["*"]));

    expect(result.current).toEqual({ allowed: true, pending: false });
  });

  it("returns pending while roles are not hydrated", () => {
    mockUseAuth.mockReturnValue({ roles: [], rolesHydrated: false });

    const { result } = renderHook(() => useRoleGuard(["qa-manager"]));

    expect(result.current).toEqual({ allowed: false, pending: true });
  });

  it("allows access when one of the required roles is present", () => {
    mockUseAuth.mockReturnValue({ roles: ["operator", "qa-manager"], rolesHydrated: true });

    const { result } = renderHook(() => useRoleGuard(["qa-manager", "it-admin"]));

    expect(result.current).toEqual({ allowed: true, pending: false });
  });

  it("denies access when no required role is present", () => {
    mockUseAuth.mockReturnValue({ roles: ["operator"], rolesHydrated: true });

    const { result } = renderHook(() => useRoleGuard(["auditor"]));

    expect(result.current).toEqual({ allowed: false, pending: false });
  });
});