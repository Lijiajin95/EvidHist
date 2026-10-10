import { defineConfig } from "@playwright/test";

// E2E uses a dedicated backend port so a demo service on 8000 is never reused.
const backendUrl = "http://127.0.0.1:8001";
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
      command:
        "bash -c 'EVIDHIST_DATABASE_URL=postgresql+psycopg://evidhist:evidhist@127.0.0.1:55432/evidhist_test ../.venv/bin/python ../scripts/migrate.py && ../.venv/bin/uvicorn evidhist.api:app --host 127.0.0.1 --port 8001'",
      url: `${backendUrl}/health/live`,
      reuseExistingServer: !ci,
      timeout: 30000,
    },
    {
      command: "npm run dev",
      url: frontendUrl,
      reuseExistingServer: !ci,
      timeout: 30000,
      env: { VITE_PROXY_TARGET: "http://127.0.0.1:8001" },
    },
  ],
};

export default defineConfig(
  ci
    ? { ...shared, workers: 2, retries: 1, forbidOnly: true, failOnFlakyTests: true }
    : { ...shared, retries: 0 },
);
