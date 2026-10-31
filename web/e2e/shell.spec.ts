import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

const BACKEND = "http://127.0.0.1:8100";
const CAMPAIGN = "/c/paratheos";
const PAGES = ["mesa", "personagens", "ficha", "cenas"] as const;

async function signIn(page: Page) {
  await page.request.post(`${BACKEND}/__test__/reset`);
  await page.request.post(`${BACKEND}/__test__/login`);
}

test("the music page keeps its own chrome without the campaign rail", async ({
  page,
}) => {
  await signIn(page);

  await page.goto("/");

  await expect(page.getByTestId("transport")).toBeVisible();
  await expect(page.getByTestId("shell-rail")).toHaveCount(0);
});

test("each campaign page renders the shell with its own mark", async ({
  page,
}) => {
  await signIn(page);

  for (const name of PAGES) {
    const response = await page.goto(`${CAMPAIGN}/${name}`);

    expect(response?.status()).toBe(200);
    await expect(page.getByTestId("shell-wordmark")).toContainText("Harpi");
    await expect(page.getByTestId("shell-campaign")).toContainText("Paratheos");
    await expect(page.getByTestId(`shell-page-${name}`)).toHaveAttribute(
      "aria-current",
      "page",
    );
    if (name === "personagens") {
      await expect(page.getByTestId("cast")).toBeVisible();
    } else {
      await expect(page.getByTestId("page-placeholder")).toBeVisible();
    }
  }

  await expect(page.getByTestId("transport")).toHaveCount(0);
});

test("the rail navigates between pages and reports the link", async ({
  page,
}) => {
  await signIn(page);

  await page.goto(`${CAMPAIGN}/mesa`);
  await expect(page.getByTestId("shell-link-state")).toHaveText("Ativo");

  await page.getByTestId("shell-page-personagens").click();

  await expect(page).toHaveURL(/\/c\/paratheos\/personagens$/);
  await expect(page.getByTestId("shell-page-personagens")).toHaveAttribute(
    "aria-current",
    "page",
  );
  await expect(page.getByTestId("shell-page-mesa")).not.toHaveAttribute(
    "aria-current",
    "page",
  );
  await expect(page.getByTestId("cast")).toContainText("Personagens");
});

test("the rail turns into a top band below 56rem", async ({ page }) => {
  await signIn(page);
  await page.setViewportSize({ width: 390, height: 844 });

  await page.goto(`${CAMPAIGN}/mesa`);

  const band = await page.getByTestId("shell-rail").boundingBox();
  const stackedMain = await page.getByTestId("shell-main").boundingBox();
  if (!band || !stackedMain) throw new Error("shell has no bounding box");
  expect(band.x).toBeLessThanOrEqual(1);
  expect(band.width).toBeGreaterThanOrEqual(389);
  expect(stackedMain.y).toBeGreaterThanOrEqual(band.y + band.height - 1);
  const scrollWidth = await page.evaluate(
    () => document.documentElement.scrollWidth,
  );
  expect(scrollWidth).toBeLessThanOrEqual(391);

  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto(`${CAMPAIGN}/mesa`);

  const rail = await page.getByTestId("shell-rail").boundingBox();
  const sideMain = await page.getByTestId("shell-main").boundingBox();
  if (!rail || !sideMain) throw new Error("shell has no bounding box");
  expect(rail.x).toBeLessThanOrEqual(1);
  expect(rail.width).toBeGreaterThan(200);
  expect(sideMain.x).toBeGreaterThanOrEqual(rail.x + rail.width - 1);
});
