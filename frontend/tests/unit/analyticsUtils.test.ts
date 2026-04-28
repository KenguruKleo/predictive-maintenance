import { describe, expect, it } from "vitest";
import type { Incident } from "../../src/types/incident";
import {
  getPeriodLabel,
  getStatusLabel,
  groupIncidentsByPeriodAndStatus,
} from "../../src/components/IncidentAnalytics/analyticsUtils";

function makeIncident(overrides: Partial<Incident> = {}): Incident {
  return {
    id: overrides.id ?? "inc-1",
    equipment_id: overrides.equipment_id ?? "MIX-102",
    severity: overrides.severity ?? "major",
    status: overrides.status ?? "open",
    ...overrides,
  };
}

describe("analyticsUtils", () => {
  it("groups incidents by day using created_at or reported_at", () => {
    const grouped = groupIncidentsByPeriodAndStatus([
      makeIncident({ id: "1", status: "open", created_at: "2026-04-28T12:00:00Z" }),
      makeIncident({ id: "2", status: "closed", reported_at: "2026-04-28T15:30:00Z" }),
      makeIncident({ id: "3", status: "approved", created_at: "not-a-date" }),
    ]);

    expect(grouped).toEqual({
      "2026-04-28": {
        open: 1,
        closed: 1,
      },
    });
  });

  it("groups incidents by week when requested", () => {
    const grouped = groupIncidentsByPeriodAndStatus([
      makeIncident({ id: "1", status: "open", created_at: "2026-01-01T12:00:00" }),
      makeIncident({ id: "2", status: "open", created_at: "2026-01-02T12:00:00" }),
    ], "week");

    const [weekKey] = Object.keys(grouped);
    expect(weekKey).toMatch(/^2026-W\d+$/);
    expect(grouped[weekKey]).toEqual({ open: 2 });
  });

  it("returns stable labels for statuses and periods", () => {
    expect(getStatusLabel("queued_for_analysis")).toBe("Queued for AI");
    expect(getStatusLabel("custom_status")).toBe("custom_status");
    expect(getPeriodLabel("2026-W18")).toBe("2026 Week 18");
    expect(getPeriodLabel("2026-04-28")).toContain("2026");
    expect(getPeriodLabel("custom-period")).toBe("custom-period");
  });
});