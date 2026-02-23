import { test, expect } from '@playwright/test';

const GUILD_NAME = "The Nosbor's Hand";
const CHANNEL_NAME = 'BRAZIL';
const MUSIC_LINK_1 = 'Warriors Imagine Dragons';

test.describe('Home Page', () => {
	test('server status displays on home page', async ({ page }) => {
		await page.goto('/');
		await expect(page.locator('text=CPU STATUS')).toBeVisible();
		await expect(page.locator('text=MEMORY FRAME')).toBeVisible();
		await expect(page.locator('.text-6xl')).toBeVisible();
	});

	test('home page loads without errors', async ({ page }) => {
		await page.goto('/');
		await expect(page.locator('text=DASHBOARD // OVERVIEW')).toBeVisible();
	});
});

test.describe('Music Page', () => {
	test('music page loads', async ({ page }) => {
		await page.goto('/music');
		await expect(page.locator('text=AUDIO // CONTROL')).toBeVisible();
	});

	test('select guild and channel', async ({ page }) => {
		await page.goto('/music');
		await page.waitForTimeout(3000);
		await page.locator('select').first().selectOption({ label: GUILD_NAME });
		await page.waitForTimeout(2000);
		await page.locator('select').nth(1).selectOption({ label: CHANNEL_NAME });
		await page.waitForTimeout(3000);
		await expect(page.locator('text=STATUS: LINKED')).toBeVisible();
	});
});

test.describe('Music Playback', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/music');
		await page.waitForTimeout(3000);
		await page.locator('select').first().selectOption({ label: GUILD_NAME });
		await page.waitForTimeout(2000);
		await page.locator('select').nth(1).selectOption({ label: CHANNEL_NAME });
		await page.waitForTimeout(4000);
	});

	test('add music to queue', async ({ page }) => {
		const input = page.locator('input[placeholder="ENTER YOUTUBE LINK..."]').first();
		await input.fill(MUSIC_LINK_1);
		await page.locator('button:has-text("[ ADD ]")').first().click();
		await page.waitForTimeout(5000);
		await expect(page.locator('text=QUEUE SEQUENCE')).toBeVisible();
	});

	test('pause button works', async ({ page }) => {
		const input = page.locator('input[placeholder="ENTER YOUTUBE LINK..."]').first();
		await input.fill(MUSIC_LINK_1);
		await page.locator('button:has-text("[ ADD ]")').first().click();
		await page.waitForTimeout(8000);
		await page.locator('button:has-text("[ PAUSE ]")').click();
		await expect(page.locator('button:has-text("[ RESUME ]")')).toBeVisible();
	});

	test('resume button works', async ({ page }) => {
		const input = page.locator('input[placeholder="ENTER YOUTUBE LINK..."]').first();
		await input.fill(MUSIC_LINK_1);
		await page.locator('button:has-text("[ ADD ]")').first().click();
		await page.waitForTimeout(8000);
		await page.locator('button:has-text("[ PAUSE ]")').click();
		await page.waitForTimeout(1000);
		await page.locator('button:has-text("[ RESUME ]")').click();
		await expect(page.locator('button:has-text("[ PAUSE ]")')).toBeVisible();
	});

	test('loop toggle is visible', async ({ page }) => {
		await expect(page.locator('button:has-text("[ LOOP:")')).toBeVisible();
	});
});

test.describe('Layers', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/music');
		await page.waitForTimeout(3000);
		await page.locator('select').first().selectOption({ label: GUILD_NAME });
		await page.waitForTimeout(2000);
		await page.locator('select').nth(1).selectOption({ label: CHANNEL_NAME });
		await page.waitForTimeout(4000);
		await page.locator('button:has-text("[ STOP ]")').click();
		await page.waitForTimeout(2000);
	});

	test('add layer', async ({ page }) => {
		const layerInput = page.locator('input[placeholder="ADD LAYER URL..."]');
		await layerInput.fill(MUSIC_LINK_1);
		await page.locator('button:has-text("[ + ]")').click();
		await page.waitForTimeout(8000);
		await expect(page.locator('text=BACKGROUND LAYERS')).toBeVisible();
	});

	test('remove layer', async ({ page }) => {
		const layerInput = page.locator('input[placeholder="ADD LAYER URL..."]');
		await layerInput.fill(MUSIC_LINK_1);
		await page.locator('button:has-text("[ + ]")').click();
		await page.waitForTimeout(8000);
		await page.locator('button:has-text("[ REMOVE ]")').first().click();
		await page.waitForTimeout(2000);
		await expect(page.locator('text=NO ACTIVE LAYERS')).toBeVisible();
	});
});

test.describe('Stop', () => {
	test('stop button clears queue', async ({ page }) => {
		await page.goto('/music');
		await page.waitForTimeout(3000);
		await page.locator('select').first().selectOption({ label: GUILD_NAME });
		await page.waitForTimeout(2000);
		await page.locator('select').nth(1).selectOption({ label: CHANNEL_NAME });
		await page.waitForTimeout(4000);
		const input = page.locator('input[placeholder="ENTER YOUTUBE LINK..."]').first();
		await input.fill(MUSIC_LINK_1);
		await page.locator('button:has-text("[ ADD ]")').first().click();
		await page.waitForTimeout(8000);
		await page.locator('button:has-text("[ STOP ]")').click();
		await page.waitForTimeout(3000);
		await expect(page.locator('text=NO AUDIO SIGNAL DETECTED')).toBeVisible();
	});
});
