import { defineConfig, devices } from "@playwright/test";

// Local E2E servers must never be routed through a developer machine's HTTP proxy.
process.env.NO_PROXY = "127.0.0.1,localhost";
process.env.no_proxy = process.env.NO_PROXY;
delete process.env.HTTP_PROXY;
delete process.env.http_proxy;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:5173",
    channel: "msedge",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop-edge", use: { ...devices["Desktop Edge"] } },
    { name: "mobile-edge", use: { viewport: { width: 390, height: 844 } } },
  ],
  webServer: [
    {
      command:
        "..\\backend\\.venv\\Scripts\\python.exe ..\\backend\\manage.py seed_demo && ..\\backend\\.venv\\Scripts\\python.exe ..\\backend\\manage.py runserver 127.0.0.1:8000 --noreload",
      url: "http://127.0.0.1:8000/api/health/",
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 5173",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: false,
      timeout: 30_000,
    },
  ],
});
