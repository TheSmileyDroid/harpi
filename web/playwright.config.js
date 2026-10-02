import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, devices } from "@playwright/test";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");

const PANEL_TOKEN = "e2e-panel-token";
const SECRET_KEY = "e2e-secret-key";
const BACKEND_PORT = 8100;

export default defineConfig({
  testDir: "./e2e",
  timeout: 30000,
  expect: { timeout: 10000 },
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: `http://127.0.0.1:${BACKEND_PORT}`,
    trace: "retain-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: [
    {
      command: "uv run python web/e2e/backend.py",
      cwd: root,
      url: `http://127.0.0.1:${BACKEND_PORT}/__test__/ping`,
      reuseExistingServer: false,
      timeout: 30000,
      env: {
        ...process.env,
        PANEL_TOKEN,
        SECRET_KEY,
        DISCORD_TOKEN: "",
        HOST: "127.0.0.1",
        PORT: String(BACKEND_PORT),
      },
    },
  ],
});
