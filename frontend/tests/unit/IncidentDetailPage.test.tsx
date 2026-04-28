import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import IncidentDetailPage from "../../src/pages/IncidentDetailPage";

const mockUseIncident = vi.fn();
const mockUseIncidentEvents = vi.fn();
const mockUseAuth = vi.fn();

vi.mock("../../src/hooks/useIncidents", () => ({
  useIncident: (...args: unknown[]) => mockUseIncident(...args),
  useIncidentEvents: (...args: unknown[]) => mockUseIncidentEvents(...args),
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

describe("IncidentDetailPage auth errors", () => {
  beforeEach(() => {
    mockUseIncident.mockReset();
    mockUseIncidentEvents.mockReset();
    mockUseAuth.mockReset();
    mockUseIncidentEvents.mockReturnValue({ data: [], error: null });
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
