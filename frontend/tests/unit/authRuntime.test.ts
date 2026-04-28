import { beforeEach, describe, expect, it } from "vitest";
import {
  clearE2EAuthState,
  getE2EAuthState,
  getE2EDecisionDefaults,
  getE2ERequestHeaders,
  setE2EPrimaryRole,
} from "../../src/authRuntime";

const STORAGE_KEY = "sentinel:e2e-auth";

describe("authRuntime", () => {
  beforeEach(() => {
    clearE2EAuthState();
  });

  it("returns predictable defaults when no auth state is stored", () => {
    expect(getE2EAuthState()).toEqual({
      userId: "ivan.petrenko",
      displayName: "Ivan Petrenko",
      email: "ivan.petrenko@local.test",
      roles: ["operator"],
    });
  });

  it("normalizes and deduplicates stored roles", () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        userId: "qa.user",
        displayName: "QA User",
        email: "qa.user@local.test",
        roles: ["QAManager", "qa-manager", "IT Administrator", "unknown"],
      }),
    );

    expect(getE2EAuthState()).toEqual({
      userId: "qa.user",
      displayName: "QA User",
      email: "qa.user@local.test",
      roles: ["qa-manager", "it-admin"],
    });
  });

  it("falls back to operator when stored roles are invalid", () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        userId: "fallback.user",
        roles: ["invalid", ""],
      }),
    );

    expect(getE2EAuthState().roles).toEqual(["operator"]);
  });

  it("persists a new primary role and derives request defaults from it", () => {
    setE2EPrimaryRole("it-admin");

    expect(getE2EAuthState().roles).toEqual(["it-admin"]);
    expect(getE2ERequestHeaders()).toEqual({
      "X-Mock-Role": "ITAdmin",
      "X-Mock-User": "ivan.petrenko",
    });
    expect(getE2EDecisionDefaults()).toEqual({
      userId: "ivan.petrenko",
      role: "it-admin",
    });
  });

  it("clears the stored auth state", () => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ roles: ["operator"] }));

    clearE2EAuthState();

    expect(window.localStorage.getItem(STORAGE_KEY)).toBeNull();
  });
});