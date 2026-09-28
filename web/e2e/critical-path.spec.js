import { expect, test } from "@playwright/test";

const PANEL_TOKEN = "e2e-panel-token";
const BACKEND = "http://127.0.0.1:8000";

test("sign in, then a pushed status change lands without a reload", async ({
  page,
  request,
}) => {
  let loads = 0;
  page.on("load", () => {
    loads += 1;
  });

  await page.goto("/");
  await expect(page.getByTestId("signin")).toBeVisible();

  await page.getByTestId("panel-token").fill("wrong-token");
  await page.getByTestId("sign-in").click();
  await expect(page.getByTestId("error-region")).toContainText(
    "Invalid panel token",
  );

  await page.getByTestId("panel-token").fill(PANEL_TOKEN);
  await page.getByTestId("sign-in").click();

  await expect(page.getByTestId("toast")).toContainText("Signed in");

  await expect(page.getByTestId("bot-status")).toHaveText("ONLINE");
  await expect(page.getByTestId("link-state")).toHaveText("LINK LIVE");
  await expect(page.getByTestId("guild-id")).toContainText("Guild 1");
  await expect(page.getByTestId("connection")).toHaveText("Linked to 42");
  await expect(page.getByTestId("now-playing")).toHaveText("Now Track");

  await request.post(`${BACKEND}/__test__/track`, {
    data: { title: "Next Track" },
  });
  await expect(page.getByTestId("now-playing")).toHaveText("Next Track");

  await request.post(`${BACKEND}/__test__/bot`, { data: { online: false } });
  await expect(page.getByTestId("bot-status")).toHaveText("OFFLINE");

  expect(loads).toBe(1);
});

test("a dropped stream reconnects and resyncs state without a reload", async ({
  page,
  request,
}) => {
  let loads = 0;
  page.on("load", () => {
    loads += 1;
  });

  let dropped = false;
  await page.route("**/api/events", async (route) => {
    if (!dropped) {
      dropped = true;
      await route.abort();
      return;
    }
    await route.continue();
  });

  await page.goto("/");
  await page.getByTestId("panel-token").fill(PANEL_TOKEN);
  await page.getByTestId("sign-in").click();

  await expect(page.getByTestId("link-state")).toHaveText("LINK LOST");

  await request.post(`${BACKEND}/__test__/track`, {
    data: { title: "Reconnect Track" },
  });

  await expect(page.getByTestId("link-state")).toHaveText("LINK LIVE", {
    timeout: 15000,
  });
  await expect(page.getByTestId("now-playing")).toHaveText("Reconnect Track");

  expect(loads).toBe(1);
});

test("a valid session skips sign-in on reload", async ({ page, context }) => {
  await page.goto("/");
  await page.getByTestId("panel-token").fill(PANEL_TOKEN);
  await page.getByTestId("sign-in").click();
  await expect(page.getByTestId("bot-status")).toBeVisible();

  await page.reload();

  await expect(page.getByTestId("signin")).toHaveCount(0);
  await expect(page.getByTestId("bot-status")).toBeVisible();
  expect(context.pages()).toHaveLength(1);
});
