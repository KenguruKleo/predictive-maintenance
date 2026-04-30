import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ApprovalPanel from "../../src/components/Approval/ApprovalPanel";
import type { Incident } from "../../src/types/incident";

const mockUseSubmitDecision = vi.fn();

vi.mock("../../src/hooks/useIncidents", () => ({
  useSubmitDecision: (...args: unknown[]) => mockUseSubmitDecision(...args),
}));

function makeIncident(overrides: Partial<Incident> = {}): Incident {
  return {
    id: "INC-2026-0049",
    incident_number: "INC-2026-0049",
    equipment_id: "GR-204",
    severity: "major",
    status: "pending_approval",
    ai_analysis: {
      risk_level: "HIGH",
      confidence: 0.82,
      evidence_citations: [],
      agent_recommendation: "APPROVE",
      agent_recommendation_rationale: "Tubing replacement is recommended based on the previous analysis.",
      recommendation: "Replace tubing before restarting the line.",
      work_order_draft: { description: "Inspect and replace tubing." },
      audit_entry_draft: { description: "Record the spray rate excursion." },
    },
    ...overrides,
  };
}

describe("ApprovalPanel follow-up submission", () => {
  beforeEach(() => {
    mockUseSubmitDecision.mockReset();
  });

  it("shows the follow-up requested block immediately after sending the question", async () => {
    const user = userEvent.setup();
    const mutate = vi.fn();
    mockUseSubmitDecision.mockReturnValue({ isPending: false, mutate });
    const question = "Compare the current case with historical incidents for GR-204.";

    render(
      <ApprovalPanel
        incident={makeIncident()}
        events={[]}
        canMakeDecision
      />,
    );

    expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Need More Info" }));
    await user.type(screen.getByPlaceholderText("Ask a detailed question..."), question);
    await user.click(screen.getByRole("button", { name: "Send question" }));

    expect(mutate).toHaveBeenCalledWith(
      { action: "more_info", question },
      expect.any(Object),
    );
    expect(await screen.findByText("Follow-up requested")).toBeInTheDocument();
    expect(screen.getByText("Question asked")).toBeInTheDocument();
    expect(screen.getByText(question)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Decline" })).not.toBeInTheDocument();
  });
});
