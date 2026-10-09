import { defineConfig } from "@playwright/test";

const backendUrl = "http://127.0.0.1:8000";
const frontendUrl = "http://127.0.0.1:5173";
const ci = process.env.CI === "true";

const shared = {
  testDir: "./tests/e2e",
  timeout: 30000,
  expect: { timeout: 5000 },
  globalTimeout: 600000,
  use: {
    baseURL: frontendUrl,
    actionTimeout: 10000,
    navigationTimeout: 15000,
    trace: "retain-on-failure" as const,
    screenshot: "only-on-failure" as const,
  },
  webServer: [
    {
      command: "../.venv/bin/uvicorn evidhist.api:app --host 127.0.0.1 --port 8000",
      url: `${backendUrl}/health/live`,
      reuseExistingServer: !ci,
      timeout: 30000,
    },
    {
      command: "npm run dev",
      url: frontendUrl,
      reuseExistingServer: !ci,
      timeout: 30000,
    },
  ],
};

export default defineConfig(
  ci
    ? { ...shared, workers: 2, retries: 1, forbidOnly: true, failOnFlakyTests: true }
    : { ...shared, retries: 0 },
);
