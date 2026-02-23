import { test, expect } from '@playwright/test';

const GUILD_NAME = "The Nosbor's Hand";
const CHANNEL_NAME = 'BRAZIL';
const SOUND_URL = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ';

test.describe('Soundboard Page', () => {
	test('soundboard page loads', async ({ page }) => {
		await page.goto('/soundboard');
		await expect(page.getByRole('heading', { name: 'SOUNDBOARD' })).toBeVisible();
	});

	test('select guild and channel', async ({ page }) => {
		await page.goto('/soundboard');
		await page.waitForTimeout(3000);
		await page.locator('select').first().selectOption({ label: GUILD_NAME });
		await page.waitForTimeout(2000);
		await page.locator('select').nth(1).selectOption({ label: CHANNEL_NAME });
		await page.waitForTimeout(3000);
		await expect(page.locator('text=STATUS:')).toBeVisible();
	});
});

test.describe('Soundboard Nodes', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/soundboard');
		await page.waitForTimeout(3000);
		await page.locator('select').first().selectOption({ label: GUILD_NAME });
		await page.waitForTimeout(2000);
		await page.locator('select').nth(1).selectOption({ label: CHANNEL_NAME });
		await page.waitForTimeout(4000);
	});

	test('add sound source', async ({ page }) => {
		const input = page.locator('input[placeholder="youtube url..."]').first();
		await input.fill(SOUND_URL);
		await page.locator('button:has-text("[ ADD ]")').first().click();
		await page.waitForTimeout(5000);
		await expect(page.locator('text=NODES (')).toBeVisible();
	});

	test('add playlist item', async ({ page }) => {
		const input = page.locator('input[placeholder="youtube url..."]').nth(1);
		await input.fill(SOUND_URL);
		await page.locator('button:has-text("[ ADD ]")').nth(1).click();
		await page.waitForTimeout(5000);
		await expect(page.locator('text=NODES (')).toBeVisible();
	});

	test('add mixer node', async ({ page }) => {
		await page.locator('button:has-text("[ + MIXER ]")').click();
		await page.waitForTimeout(2000);
		await expect(page.locator('button:has-text("[ + MIXER ]")')).toBeVisible();
		await expect(page.getByText('mixer', { exact: true })).toBeVisible();
	});
});
