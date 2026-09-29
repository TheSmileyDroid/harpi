import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, devices } from "@playwright/test";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");

const PANEL_TOKEN = "e2e-panel-token";
const SECRET_KEY = "e2e-secret-key";
const FRONTEND_PORT = 5273;
const BACKEND_PORT = 8100;

export default defineConfig({
  testDir: "./e2e",
  timeout: 30000,
  expect: { timeout: 10000 },
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: `http://127.0.0.1:${FRONTEND_PORT}`,
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
    {
      command: `bun run dev --host 127.0.0.1 --port ${FRONTEND_PORT} --strictPort`,
      cwd: here,
      url: `http://127.0.0.1:${FRONTEND_PORT}`,
      reuseExistingServer: false,
      timeout: 60000,
      env: {
        ...process.env,
        API_TARGET: `http://127.0.0.1:${BACKEND_PORT}`,
      },
    },
  ],
});
