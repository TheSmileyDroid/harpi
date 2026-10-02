import { expect, test } from "@playwright/test";

const PANEL_TOKEN = "e2e-panel-token";
const BACKEND = "http://127.0.0.1:8100";
const GUILD_B = 2;
const GUILD_B_CHANNEL = GUILD_B * 10;

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

test("selects a shared guild, connects to a voice channel, then disconnects", async ({
  page,
  request,
}) => {
  await request.post(`${BACKEND}/__test__/bot`, { data: { online: true } });
  await page.goto("/");
  await page.getByTestId("panel-token").fill(PANEL_TOKEN);
  await page.getByTestId("sign-in").click();
  await expect(page.getByTestId("bot-status")).toHaveText("ONLINE");

  await expect(page.getByTestId("guild-select").locator("option")).toHaveCount(
    3,
  );
  await expect(page.getByTestId("guild-select")).toContainText("Beta Guild");

  await page.getByTestId("guild-select").selectOption(String(GUILD_B));
  await expect(page.getByTestId("channel-select")).toContainText("Channel 2");
  await page
    .getByTestId("channel-select")
    .selectOption(String(GUILD_B_CHANNEL));

  await page.getByTestId("connect").click();

  await expect(page.getByTestId("connection")).toHaveText(
    `Linked to ${GUILD_B_CHANNEL}`,
  );
  await expect(page.getByTestId("toasts")).toContainText("Connected");

  await page.getByTestId("disconnect").click();

  await expect(page.getByTestId("connection")).toHaveText("Not connected");
});

test("searches, queues, and removes, with queue changes live over SSE", async ({
  page,
  request,
}) => {
  await request.post(`${BACKEND}/__test__/reset`);
  let loads = 0;
  page.on("load", () => {
    loads += 1;
  });

  await page.goto("/");
  await page.getByTestId("panel-token").fill(PANEL_TOKEN);
  await page.getByTestId("sign-in").click();
  await expect(page.getByTestId("bot-status")).toHaveText("ONLINE");

  await page.getByTestId("search-input").fill("daft punk");
  await expect(page.getByTestId("search-result").first()).toContainText(
    "Found daft punk",
  );

  await page.getByTestId("queue-track").first().click();
  await expect(page.getByTestId("toasts")).toContainText("Added to queue");
  await expect(page.getByTestId("queue-row").first()).toContainText(
    "daft punk",
  );

  await page.getByTestId("queue-remove").first().click();
  await expect(page.getByTestId("confirm-dialog")).toBeVisible();
  await page.getByTestId("confirm-execute").click();
  await expect(page.getByTestId("toasts")).toContainText("Removed from queue");
  await expect(page.getByTestId("queue-empty")).toContainText("Queue empty");

  await request.post(`${BACKEND}/__test__/enqueue`, {
    data: { url: "https://example.com/Live" },
  });
  await expect(page.getByTestId("queue-row").first()).toContainText("Live");

  expect(loads).toBe(1);
});
