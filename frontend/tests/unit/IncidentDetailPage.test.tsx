import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import IncidentDetailPage from "../../src/pages/IncidentDetailPage";
import type { Incident, IncidentEvent } from "../../src/types/incident";

const mockUseIncident = vi.fn();
const mockUseIncidentEvents = vi.fn();
const mockUseSubmitDecision = vi.fn();
const mockUseAuth = vi.fn();

vi.mock("../../src/hooks/useIncidents", () => ({
  useIncident: (...args: unknown[]) => mockUseIncident(...args),
  useIncidentEvents: (...args: unknown[]) => mockUseIncidentEvents(...args),
  useSubmitDecision: (...args: unknown[]) => mockUseSubmitDecision(...args),
}));

vi.mock("../../src/hooks/useAuth", () => ({
  useAuth: () => mockUseAuth(),
}));

function makeAxiosError(status: number, message: string) {
  return {
    isAxiosError: true,
    message,
    response: {
      status,
      data: { error: message },
    },
  };
}

function renderIncidentDetail() {
  render(
    <MemoryRouter initialEntries={["/incidents/INC-2026-0110"]}>
      <Routes>
        <Route path="/incidents/:id" element={<IncidentDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

function makeIncident(overrides: Partial<Incident> = {}): Incident {
  return {
    id: "INC-2026-0049",
    incident_number: "INC-2026-0049",
    title: "Spray rate excursion",
    equipment_id: "GR-204",
    batch_id: "B-0049",
    product: "Metformin HCl 500mg",
    production_stage: "Granulation",
    severity: "major",
    status: "queued_for_analysis",
    workflow_state: {
      current_step: "queued_for_analysis_followup",
      target_role: "operator",
    },
    ai_analysis: {
      risk_level: "HIGH",
      confidence: 0.82,
      evidence_citations: [],
      agent_recommendation: "APPROVE",
      agent_recommendation_rationale: "Tubing replacement is recommended based on the previous analysis.",
      recommendation: "Replace tubing before restarting the line.",
      batch_disposition: "hold",
    },
    lastDecision: {
      action: "more_info",
      user_id: "operator.user",
      role: "operator",
      question: "Compare the current case with historical incidents for GR-204.",
    },
    ...overrides,
  };
}

function makeFollowUpEvent(overrides: Partial<IncidentEvent> = {}): IncidentEvent {
  return {
    id: "INC-2026-0049-more-info",
    incident_id: "INC-2026-0049",
    timestamp: "2026-04-30T10:01:00Z",
    actor: "operator.user",
    actor_type: "human",
    action: "more_info",
    details: "Compare the current case with historical incidents for GR-204.",
    status: "queued_for_analysis",
    ...overrides,
  };
}

describe("IncidentDetailPage auth errors", () => {
  beforeEach(() => {
    mockUseIncident.mockReset();
    mockUseIncidentEvents.mockReset();
    mockUseSubmitDecision.mockReset();
    mockUseAuth.mockReset();
    mockUseIncidentEvents.mockReturnValue({ data: [], error: null });
    mockUseSubmitDecision.mockReturnValue({ isPending: false, mutate: vi.fn() });
    mockUseAuth.mockReturnValue({
      hasAnyRole: vi.fn(() => false),
      hasRole: vi.fn(() => false),
    });
  });

  it("shows sign-in recovery copy for API 401 errors", () => {
    mockUseIncident.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: makeAxiosError(401, "Authentication required"),
    });

    renderIncidentDetail();

    expect(screen.getByText("Session expired. Redirecting to sign-in...")).toBeInTheDocument();
  });

  it("shows access denied copy for API 403 errors", () => {
    mockUseIncident.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: makeAxiosError(403, "No Sentinel app role assigned"),
    });

    renderIncidentDetail();

    expect(screen.getByText("You do not have access to this incident.")).toBeInTheDocument();
  });

  it("keeps not-found copy for API 404 errors", () => {
    mockUseIncident.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: makeAxiosError(404, "Incident not found"),
    });

    renderIncidentDetail();

    expect(screen.getByText("Incident not found.")).toBeInTheDocument();
  });
});

describe("IncidentDetailPage follow-up waiting state", () => {
  beforeEach(() => {
    mockUseIncident.mockReset();
    mockUseIncidentEvents.mockReset();
    mockUseSubmitDecision.mockReset();
    mockUseAuth.mockReset();
    mockUseSubmitDecision.mockReturnValue({ isPending: false, mutate: vi.fn() });
    mockUseAuth.mockReturnValue({
      hasAnyRole: vi.fn((...roles: string[]) => roles.includes("operator")),
      hasRole: vi.fn((role: string) => role === "operator"),
    });
  });

  it("keeps a queued follow-up in waiting mode instead of presenting the old recommendation as active", () => {
    mockUseIncident.mockReturnValue({
      data: makeIncident(),
      isLoading: false,
      error: null,
    });
    mockUseIncidentEvents.mockReturnValue({
      data: [makeFollowUpEvent()],
      error: null,
    });

    renderIncidentDetail();

    expect(screen.getByText("Awaiting agent response")).toBeInTheDocument();
    expect(screen.getByText("Follow-up requested")).toBeInTheDocument();
    expect(screen.getByText("Previous AI Recommendation")).toBeInTheDocument();
    expect(screen.queryByText("AI Recommendation for this Incident")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument();
    expect(
      screen.getAllByText("Compare the current case with historical incidents for GR-204.").length,
    ).toBeGreaterThan(0);
  });

  it("shows the follow-up request block immediately for an optimistic awaiting_agents event", () => {
    mockUseIncident.mockReturnValue({
      data: makeIncident({
        status: "awaiting_agents",
        workflow_state: { current_step: "awaiting_operator_decision", target_role: "operator" },
        lastDecision: undefined,
      }),
      isLoading: false,
      error: null,
    });
    mockUseIncidentEvents.mockReturnValue({
      data: [makeFollowUpEvent({ status: "awaiting_agents" })],
      error: null,
    });

    renderIncidentDetail();

    expect(screen.getByText("Follow-up requested")).toBeInTheDocument();
    expect(screen.getByText("Question asked")).toBeInTheDocument();
    expect(screen.queryByText("Decision outcome")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument();
  });
});
