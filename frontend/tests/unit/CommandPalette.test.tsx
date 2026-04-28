import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CommandPalette from "../../src/components/Layout/CommandPalette";
import type { Incident } from "../../src/types/incident";

const mockNavigate = vi.fn();
const mockUseAuth = vi.fn();
const mockUseIncidents = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock("../../src/hooks/useAuth", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("../../src/hooks/useIncidents", () => ({
  useIncidents: () => mockUseIncidents(),
}));

function makeIncident(overrides: Partial<Incident> = {}): Incident {
  return {
    id: overrides.id ?? "inc-1",
    equipment_id: overrides.equipment_id ?? "MIX-102",
    severity: overrides.severity ?? "major",
    status: overrides.status ?? "pending_approval",
    incident_number: overrides.incident_number ?? "INC-2026-0001",
    title: overrides.title ?? "Mixer vibration high",
    ...overrides,
  };
}

describe("CommandPalette", () => {
  beforeEach(() => {
    mockNavigate.mockReset();
    mockUseAuth.mockReset();
    mockUseIncidents.mockReset();
    mockUseAuth.mockReturnValue({ roles: ["it-admin"] });
    mockUseIncidents.mockReturnValue({
      data: {
        items: [makeIncident()],
      },
    });
  });

  it("shows role-gated navigation commands for IT admin users", () => {
    render(<CommandPalette open onClose={vi.fn()} />);

    expect(screen.getByText("Document Templates")).toBeInTheDocument();
    expect(screen.getByText("Incident Telemetry")).toBeInTheDocument();
    expect(screen.getByText("INC-2026-0001")).toBeInTheDocument();
  });

  it("filters commands and navigates with keyboard selection", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    render(<CommandPalette open onClose={onClose} />);

    const input = screen.getByPlaceholderText("Search pages, incidents…");
    await user.type(input, "template");

    expect(screen.getByText("Document Templates")).toBeInTheDocument();
    expect(screen.queryByText("Operations Dashboard")).not.toBeInTheDocument();

    await user.keyboard("{Enter}");

    expect(mockNavigate).toHaveBeenCalledWith("/templates");
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});