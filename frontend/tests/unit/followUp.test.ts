import { describe, expect, it } from "vitest";
import {
  getLatestFollowUpRequest,
  getPendingFollowUpState,
  isIncidentFollowUpProcessing,
} from "../../src/utils/followUp";
import type { Incident, IncidentEvent } from "../../src/types/incident";

function makeIncident(overrides: Partial<Incident> = {}): Incident {
  return {
    id: "INC-2026-0049",
    equipment_id: "GR-204",
    severity: "major",
    status: "queued_for_analysis",
    workflow_state: { current_step: "queued_for_analysis_followup" },
    lastDecision: {
      action: "more_info",
      question: "Compare the current case with historical incidents for GR-204.",
    },
    ...overrides,
  };
}

function makeEvent(overrides: Partial<IncidentEvent> = {}): IncidentEvent {
  return {
    id: overrides.id ?? "event-1",
    incident_id: overrides.incident_id ?? "INC-2026-0049",
    timestamp: overrides.timestamp ?? "2026-04-30T10:00:00Z",
    actor: overrides.actor ?? "operator.user",
    actor_type: overrides.actor_type ?? "human",
    action: overrides.action ?? "more_info",
    details: overrides.details ?? "Compare the current case with historical incidents for GR-204.",
    ...overrides,
  };
}

describe("getPendingFollowUpState", () => {
  it("keeps a follow-up pending while the rerun is queued", () => {
    const state = getPendingFollowUpState(makeIncident(), [
      makeEvent({ action: "more_info", timestamp: "2026-04-30T10:01:00Z" }),
      makeEvent({
        id: "initial-response",
        actor: "AI Agent",
        actor_type: "agent",
        action: "agent_response",
        message_kind: "initial_recommendation",
        timestamp: "2026-04-30T09:59:00Z",
      }),
    ]);

    expect(state).toEqual({
      isPending: true,
      question: "Compare the current case with historical incidents for GR-204.",
      requestedAt: "2026-04-30T10:01:00Z",
    });
  });

  it("uses lastDecision after refresh when events have not loaded the question yet", () => {
    const state = getPendingFollowUpState(makeIncident({ status: "analyzing" }), []);

    expect(state).toEqual({
      isPending: true,
      question: "Compare the current case with historical incidents for GR-204.",
    });
  });

  it("extracts an optimistic request event before lastDecision is available", () => {
    const incident = makeIncident({ lastDecision: undefined, status: "awaiting_agents" });
    const events = [makeEvent({ action: "more_info", timestamp: "2026-04-30T10:01:00Z" })];

    expect(getLatestFollowUpRequest(incident, events)).toEqual({
      question: "Compare the current case with historical incidents for GR-204.",
      requestedAt: "2026-04-30T10:01:00Z",
    });
    expect(isIncidentFollowUpProcessing(incident)).toBe(true);
    expect(getPendingFollowUpState(incident, events).isPending).toBe(true);
  });

  it("clears pending state after an agent response newer than the question", () => {
    const state = getPendingFollowUpState(
      makeIncident({ status: "pending_approval", workflow_state: { current_step: "awaiting_operator_decision" } }),
      [
        makeEvent({ action: "more_info", timestamp: "2026-04-30T10:01:00Z" }),
        makeEvent({
          id: "follow-up-response",
          actor: "AI Agent",
          actor_type: "agent",
          action: "agent_response",
          message_kind: "follow_up_response",
          timestamp: "2026-04-30T10:03:00Z",
        }),
      ],
    );

    expect(state).toEqual({ isPending: false });
  });
});
