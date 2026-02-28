import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
	testDir: './tests/e2e',
	fullyParallel: false,
	workers: 1,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 2 : 0,
	reporter: 'list',
	use: {
		baseURL: 'http://localhost:3000',
		trace: 'on-first-retry',
	},
	projects: [
		{
			name: 'chromium',
			use: { ...devices['Desktop Chrome'] },
		},
	],
	webServer: [
		{
			command: 'bun run dev --port 3000',
			port: 3000,
			reuseExistingServer: !process.env.CI,
			stdout: 'pipe',
			stderr: 'pipe',
		},
		{
			command: 'uv run uvicorn app:asgi_app --port 8000',
			port: 8000,
			reuseExistingServer: !process.env.CI,
			stdout: 'pipe',
			stderr: 'pipe',
			cwd: '..',
		}
	],
});
