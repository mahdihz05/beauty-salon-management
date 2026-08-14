import { defineConfig, devices } from "@playwright/test";

// Local E2E servers must never be routed through a developer machine's HTTP proxy.
process.env.NO_PROXY = "127.0.0.1,localhost";
process.env.no_proxy = process.env.NO_PROXY;
delete process.env.HTTP_PROXY;
delete process.env.http_proxy;

const frontendPort = Number(process.env.E2E_FRONTEND_PORT ?? "5173");
const backendPort = Number(process.env.E2E_BACKEND_PORT ?? "8000");
const frontendUrl = `http://127.0.0.1:${frontendPort}`;
const backendUrl = `http://127.0.0.1:${backendPort}`;
process.env.VITE_DEV_API_PROXY = backendUrl;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  // The local E2E database is SQLite. A single worker keeps OTP/booking writes
  // deterministic; production concurrency is covered against PostgreSQL.
  workers: 1,
  preserveOutput: "always",
  retries: 0,
  reporter: "list",
  use: {
    baseURL: frontendUrl,
    channel: "msedge",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop-edge", use: { ...devices["Desktop Edge"] } },
    {
      name: "tablet-edge",
      use: {
        viewport: { width: 768, height: 1024 },
        deviceScaleFactor: 1,
        isMobile: false,
        hasTouch: true,
      },
    },
    { name: "mobile-edge", use: { viewport: { width: 390, height: 844 } } },
  ],
  webServer: [
    {
      command: `..\\backend\\.venv\\Scripts\\python.exe ..\\backend\\manage.py seed_demo && ..\\backend\\.venv\\Scripts\\python.exe ..\\backend\\manage.py runserver 127.0.0.1:${backendPort} --noreload`,
      url: `${backendUrl}/api/health/`,
      reuseExistingServer: false,
      stdout: "ignore",
      stderr: "ignore",
      timeout: 30_000,
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${frontendPort}`,
      url: frontendUrl,
      reuseExistingServer: false,
      stdout: "ignore",
      stderr: "ignore",
      timeout: 30_000,
    },
  ],
});
