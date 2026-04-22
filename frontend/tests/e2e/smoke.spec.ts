import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const STORAGE_KEY = "sentinel:e2e-auth";

type TestRole = "operator" | "it-admin" | "qa-manager";

interface TestAuthState {
  userId: string;
  displayName: string;
  email: string;
  roles: TestRole[];
}

function toMockRoleHeader(role: TestRole): string {
  if (role === "it-admin") return "ITAdmin";
  if (role === "qa-manager") return "QAManager";
  return "Operator";
}

async function applyMockAuth(page: Page, authState: TestAuthState): Promise<void> {
  await page.addInitScript(
    ([storageKey, value]) => {
      window.localStorage.setItem(storageKey, JSON.stringify(value));
    },
    [STORAGE_KEY, authState] as const,
  );
}

function buildMockHeaders(authState: TestAuthState): Record<string, string> {
  return {
    "X-Mock-Role": authState.roles.map((role) => toMockRoleHeader(role)).join(","),
    "X-Mock-User": authState.userId,
    "X-Mock-User-Id": authState.userId,
  };
}

async function fetchFirstIncidentId(
  request: APIRequestContext,
  authState: TestAuthState,
): Promise<string> {
  const response = await request.get("/api/incidents", {
    headers: buildMockHeaders(authState),
  });

  expect(response.ok()).toBeTruthy();

  const data = await response.json() as { items?: Array<{ id?: string }> } | Array<{ id?: string }>;
  const items = Array.isArray(data) ? data : data.items ?? [];
  expect(items.length).toBeGreaterThan(0);

  const incidentId = items[0]?.id;
  expect(incidentId).toBeTruthy();

  return incidentId!;
}

async function fetchFirstTemplateName(
  request: APIRequestContext,
  authState: TestAuthState,
): Promise<string> {
  const response = await request.get("/api/templates", {
    headers: buildMockHeaders(authState),
  });

  expect(response.ok()).toBeTruthy();

  const data = await response.json() as { items?: Array<{ name?: string }> } | Array<{ name?: string }>;
  const items = Array.isArray(data) ? data : data.items ?? [];
  expect(items.length).toBeGreaterThan(0);

  const templateName = items[0]?.name;
  expect(templateName).toBeTruthy();

  return templateName!;
}

test("operator dashboard loads without Entra login", async ({ page }) => {
  const authState: TestAuthState = {
    userId: "operator.smoke",
    displayName: "Operator Smoke",
    email: "operator.smoke@local.test",
    roles: ["operator"],
  };

  await applyMockAuth(page, authState);
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Operations Dashboard" })).toBeVisible();
  await expect(page.getByText(authState.displayName)).toBeVisible();
  await expect(page.getByRole("link", { name: /History & Audit/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /Templates/ })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Sign in with Microsoft/i })).toHaveCount(0);
});

test("it admin can open templates in e2e mode", async ({ page, request }) => {
  const authState: TestAuthState = {
    userId: "admin.smoke",
    displayName: "Admin Smoke",
    email: "admin.smoke@local.test",
    roles: ["it-admin"],
  };

  await applyMockAuth(page, authState);

  const templateName = await fetchFirstTemplateName(request, authState);

  await page.goto("/templates");

  await expect(page.getByRole("heading", { name: "Document Templates" })).toBeVisible();
  await expect(page.getByText(templateName)).toBeVisible();
  await expect(page.getByRole("link", { name: /Templates/ })).toBeVisible();
});

test("it admin can navigate from incident detail to telemetry", async ({ page, request }) => {
  const authState: TestAuthState = {
    userId: "admin.smoke",
    displayName: "Admin Smoke",
    email: "admin.smoke@local.test",
    roles: ["it-admin"],
  };

  await applyMockAuth(page, authState);

  const incidentId = await fetchFirstIncidentId(request, authState);

  await page.goto(`/incidents/${encodeURIComponent(incidentId)}`);

  const telemetryLink = page.getByRole("link", { name: "View Telemetry" });
  await expect(telemetryLink).toBeVisible();

  await telemetryLink.click();

  await expect(page).toHaveURL(new RegExp(`/telemetry\\?incidentId=${incidentId}$`));
  await expect(page.getByRole("heading", { name: "Incident Telemetry" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Operations Dashboard" })).toHaveCount(0);
});

test("qa-manager dashboard loads recent decisions with infinite scroll", async ({ page }) => {
  const authState: TestAuthState = {
    userId: "manager.smoke",
    displayName: "Manager Smoke",
    email: "manager.smoke@local.test",
    roles: ["qa-manager"],
  };

  await applyMockAuth(page, authState);
  await page.goto("/manager");

  await expect(page.getByRole("heading", { name: "Manager Dashboard" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Recent Decisions" })).toBeVisible();

  // Table should render at least one row once data loads
  const firstRow = page.locator(".incident-table tbody tr").first();
  await expect(firstRow).toBeVisible({ timeout: 10_000 });

  // Clickable row — clicking incident number link navigates to incident detail
  const firstLink = page.locator(".incident-table tbody .table-id-link").first();
  const incidentNumber = await firstLink.textContent();
  expect(incidentNumber).toMatch(/INC-/);

  await firstLink.click();
  await expect(page).toHaveURL(new RegExp(`/incidents/${incidentNumber}`));
});