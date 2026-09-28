import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, devices } from "@playwright/test";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");

const PANEL_TOKEN = "e2e-panel-token";
const SECRET_KEY = "e2e-secret-key";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30000,
  expect: { timeout: 10000 },
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://localhost:5173",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: [
    {
      command: "uv run python web/e2e/backend.py",
      cwd: root,
      url: "http://127.0.0.1:8000/__test__/ping",
      reuseExistingServer: false,
      timeout: 30000,
      env: {
        ...process.env,
        PANEL_TOKEN,
        SECRET_KEY,
        DISCORD_TOKEN: "",
        HOST: "127.0.0.1",
        PORT: "8000",
      },
    },
    {
      command: "bun run dev",
      cwd: here,
      url: "http://localhost:5173",
      reuseExistingServer: false,
      timeout: 60000,
    },
  ],
});
