import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, devices } from "@playwright/test";

const frontendDir = path.dirname(fileURLToPath(import.meta.url));
const backendDir = path.resolve(frontendDir, "../backend");

const frontendBaseUrl = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:4173";
const backendBaseUrl = process.env.PLAYWRIGHT_BACKEND_BASE_URL ?? "http://127.0.0.1:7072";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI
    ? [["list"], ["html", { open: "never" }]]
    : [["list"]],
  use: {
    baseURL: frontendBaseUrl,
    trace: "on-first-retry",
  },
  webServer: [
    {
      command: "npm run dev:e2e",
      cwd: frontendDir,
      url: frontendBaseUrl,
      name: "Frontend",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        ...process.env,
        VITE_AUTH_MODE: "e2e",
        VITE_API_BASE_URL: "/api",
        SENTINEL_LOCAL_API_URL: backendBaseUrl,
      },
    },
    {
      command: "func start --port 7072",
      cwd: backendDir,
      url: `${backendBaseUrl}/api/incidents`,
      name: "Backend",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        ...process.env,
        USE_LOCAL_MOCK_AUTH: "true",
      },
    },
  ],
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
      },
    },
  ],
});