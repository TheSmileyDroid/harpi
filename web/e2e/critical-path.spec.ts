import { expect, test } from "@playwright/test";

const PANEL_TOKEN = "e2e-panel-token";
const BACKEND = "http://127.0.0.1:8100";
const GUILD_B = "734174030701264912";
const GUILD_B_CHANNEL_NAME = `Channel ${GUILD_B}`;

async function signIn(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.getByTestId("panel-token").fill(PANEL_TOKEN);
  await page.getByTestId("sign-in").click();
  await expect(page.getByTestId("bot-status")).toHaveText("ONLINE");
}

async function openSearch(page: import("@playwright/test").Page) {
  await page.getByTestId("open-search").click();
  await expect(page.getByTestId("search-input")).toBeVisible();
}

async function openOutput(page: import("@playwright/test").Page) {
  await page.getByTestId("output-picker").click();
  await expect(page.getByTestId("guild-select")).toBeVisible();
}

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
  await expect(page.getByTestId("guild-id")).toContainText("Alpha Guild");
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
  await signIn(page);

  await expect(page.getByTestId("guild-id")).toContainText("Alpha Guild");
  await openOutput(page);

  await page.getByTestId("guild-select").click();
  await expect(page.getByTestId("guild-option")).toHaveCount(2);
  await page
    .getByTestId("guild-option")
    .filter({ hasText: "Beta Guild" })
    .click();
  await expect(page.getByTestId("guild-select")).toContainText("Beta Guild");

  await page.getByTestId("channel-select").click();
  await page
    .getByTestId("channel-option")
    .filter({ hasText: GUILD_B_CHANNEL_NAME })
    .click();
  await expect(page.getByTestId("channel-select")).toContainText(
    GUILD_B_CHANNEL_NAME,
  );

  await page.getByTestId("connect").click();

  await expect(page.getByTestId("connection")).toHaveText(
    `Linked to ${GUILD_B_CHANNEL_NAME}`,
  );
  await expect(page.getByTestId("toasts")).toContainText("Connected");
  await expect(page.getByTestId("guild-id")).toContainText("Beta Guild");

  await page.getByTestId("disconnect").click();
  await expect(page.getByTestId("disconnect-confirm")).toBeVisible();
  await page.getByTestId("disconnect-confirm-cancel").click();
  await expect(page.getByTestId("disconnect-confirm")).toBeHidden();
  await expect(page.getByTestId("connection")).toHaveText(
    `Linked to ${GUILD_B_CHANNEL_NAME}`,
  );

  await page.getByTestId("disconnect").click();
  await page.getByTestId("disconnect-confirm-execute").click();

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

  await signIn(page);

  await openSearch(page);
  await page.getByTestId("search-input").fill("daft punk");
  await expect(page.getByTestId("search-result").first()).toContainText(
    "Found daft punk",
  );
  await expect(page.getByTestId("search-result").first()).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(page.getByTestId("search-selection")).toContainText(
    "Found daft punk",
  );

  await page.getByTestId("queue-track").click();
  await expect(page.getByTestId("toasts")).toContainText("Added to queue");
  await expect(page.getByTestId("queue-row").first()).toContainText(
    "daft punk",
  );

  await page.getByTestId("queue-remove").first().click();
  await expect(page.getByTestId("toasts")).toContainText("Removed from queue");
  await expect(page.getByTestId("queue-empty")).toContainText("Queue empty");

  await page.getByTestId("toast-action").click();
  await expect(page.getByTestId("queue-row").first()).toContainText(
    "daft punk",
  );

  await page.getByTestId("queue-remove").first().click();
  await expect(page.getByTestId("queue-empty")).toContainText("Queue empty");

  await request.post(`${BACKEND}/__test__/enqueue`, {
    data: { url: "https://example.com/Live" },
  });
  await expect(page.getByTestId("queue-row").first()).toContainText("Live");

  expect(loads).toBe(1);
});

test("a pasted link resolves to a row and waits for confirmation", async ({
  page,
  request,
}) => {
  await request.post(`${BACKEND}/__test__/reset`);
  await signIn(page);

  await openSearch(page);
  await page.getByTestId("search-input").fill("https://example.com/song");

  await expect(page.getByTestId("search-result").first()).toContainText(
    "Found https://example.com/song",
  );
  await expect(page.getByTestId("search-selection")).toContainText(
    "Found https://example.com/song",
  );
  await expect(page.getByTestId("queue-row")).toHaveCount(0);

  await page.getByTestId("queue-track").click();
  await expect(page.getByTestId("toasts")).toContainText("Added to queue");
  await expect(page.getByTestId("queue-row").first()).toContainText(
    "https://example.com/song",
  );
});

test("the search dialog closes only on the backdrop, not on inner clicks", async ({
  page,
  request,
}) => {
  await request.post(`${BACKEND}/__test__/reset`);
  await signIn(page);

  await openSearch(page);
  await page.getByTestId("search-input").fill("daft punk");
  await expect(page.getByTestId("search-result").first()).toBeVisible();

  const panel = page.getByTestId("search-panel");
  const box = await panel.boundingBox();
  if (!box) throw new Error("search panel has no box");
  await panel.click({ position: { x: box.width - 2, y: 2 } });
  await expect(panel).toBeVisible();
  await expect(page.getByTestId("search-input")).toBeVisible();

  const input = page.getByTestId("search-input");
  const inputBox = await input.boundingBox();
  if (!inputBox) throw new Error("search input has no box");
  await page.mouse.move(inputBox.x + 8, inputBox.y + inputBox.height / 2);
  await page.mouse.down();
  await page.mouse.move(2, 2);
  await page.mouse.up();
  await expect(panel).toBeVisible();

  await page.getByTestId("search-clear").click();
  await expect(input).toHaveValue("");
  await expect(panel).toBeVisible();

  await page.mouse.click(2, 2);
  await expect(panel).toBeHidden();
});

test("drives transport, seeks, and changes volume against live position", async ({
  page,
  request,
}) => {
  await request.post(`${BACKEND}/__test__/reset`);
  let loads = 0;
  page.on("load", () => {
    loads += 1;
  });

  let statusRequests = 0;
  await page.route("**/api/status", async (route) => {
    statusRequests += 1;
    await route.continue();
  });

  await signIn(page);
  const bootStatusRequests = statusRequests;
  expect(bootStatusRequests).toBe(1);

  await request.post(`${BACKEND}/__test__/progress`, {
    data: { position: 60 },
  });
  await expect(page.getByTestId("progress-readout")).toContainText(
    "1:00 / 2:00",
  );
  expect(statusRequests).toBe(bootStatusRequests);

  await page.getByTestId("play-pause").click();
  await expect(page.getByTestId("play-pause")).toHaveText("Play");
  await expect(page.getByTestId("playback-state")).toHaveText("Paused");

  const track = page.getByTestId("seek-track");
  const box = await track.boundingBox();
  if (!box) throw new Error("seek track has no bounding box");
  const midY = box.y + box.height / 2;
  await page.mouse.click(box.x + box.width * 0.75, midY);
  await expect(page.getByTestId("progress-readout")).toContainText(
    "1:30 / 2:00",
  );

  await page.mouse.move(box.x + box.width * 0.2, midY);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.41, midY);
  await page.mouse.up();
  await expect(page.getByTestId("progress-readout")).toContainText(
    "0:49 / 2:00",
  );

  const volumeSent = page.waitForResponse((response) =>
    response.url().includes("/api/playback/volume"),
  );
  await page.getByTestId("volume-slider").evaluate((element) => {
    const input = element as HTMLInputElement;
    for (const value of ["0.3", "0.4", "0.5"]) {
      input.value = value;
      input.dispatchEvent(new Event("input", { bubbles: true }));
    }
  });
  await volumeSent;
  await expect(page.getByTestId("volume-value")).toHaveText("25%");

  const calls = (await (
    await request.get(`${BACKEND}/__test__/calls`)
  ).json()) as {
    calls: unknown[];
  };
  const volumeCalls = calls.calls.filter(
    (call): call is [string, ...unknown[]] =>
      Array.isArray(call) &&
      typeof call[0] === "string" &&
      call[0] === "set_volume",
  );
  expect(volumeCalls).toHaveLength(1);

  expect(loads).toBe(1);
});

test("adds a layer, changes its volume, and removes it with confirmation", async ({
  page,
  request,
}) => {
  await request.post(`${BACKEND}/__test__/reset`);
  let loads = 0;
  page.on("load", () => {
    loads += 1;
  });

  await signIn(page);

  await openSearch(page);
  await page.getByTestId("search-input").fill("daft punk");
  await expect(page.getByTestId("search-result").first()).toContainText(
    "Found daft punk",
  );

  await page.getByTestId("search-result").first().hover();
  await page.getByTestId("layer-track").first().click();
  await expect(page.getByTestId("toasts")).toContainText("Added as layer");
  await expect(page.getByTestId("layer-row").first()).toContainText(
    "daft punk",
  );

  const layerVolumeSent = page.waitForResponse((response) =>
    response.url().includes("/api/layers/volume"),
  );
  await page
    .getByTestId("layer-volume")
    .first()
    .evaluate((element) => {
      const input = element as HTMLInputElement;
      input.value = "0.5";
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
  await layerVolumeSent;
  await expect(page.getByTestId("layer-volume-value")).toHaveText("25%");

  await page.getByTestId("layer-remove").first().click();
  await expect(page.getByTestId("layer-confirm-dialog")).toBeVisible();
  await expect(page.getByTestId("layer-row").first()).toContainText(
    "daft punk",
  );
  await page.getByTestId("layer-confirm-cancel").click();
  await expect(page.getByTestId("layer-confirm-dialog")).toBeHidden();
  await expect(page.getByTestId("layer-row").first()).toContainText(
    "daft punk",
  );

  await page.getByTestId("layer-remove").first().click();
  await expect(page.getByTestId("layer-confirm-dialog")).toBeVisible();
  await page.getByTestId("layer-confirm-execute").click();
  await expect(page.getByTestId("toasts")).toContainText("Layer removed");
  await expect(page.getByTestId("layers-empty")).toContainText("No layers");

  const calls = (await (
    await request.get(`${BACKEND}/__test__/calls`)
  ).json()) as {
    calls: unknown[];
  };
  const layerCalls = calls.calls.filter(
    (call): call is [string, ...unknown[]] =>
      Array.isArray(call) &&
      typeof call[0] === "string" &&
      call[0].includes("layer"),
  );
  expect(layerCalls.map((call) => call[0])).toEqual([
    "add_layer",
    "set_layer_volume",
    "remove_layer",
  ]);

  expect(loads).toBe(1);
});

test("seek is keyboard-operable and results expose a listbox", async ({
  page,
  request,
}) => {
  await request.post(`${BACKEND}/__test__/reset`);
  await signIn(page);

  const seek = page.getByTestId("seek-track");
  await seek.focus();
  await expect(seek).toBeFocused();
  await page.keyboard.press("End");
  await expect(page.getByTestId("progress-readout")).toContainText(
    "2:00 / 2:00",
  );

  await openSearch(page);
  await page.getByTestId("search-input").fill("daft punk");
  await expect(
    page.getByRole("listbox", { name: "Search results" }),
  ).toBeVisible();
  await page.keyboard.press("ArrowDown");
  await expect(page.getByRole("option").first()).toHaveAttribute(
    "aria-selected",
    "true",
  );
});

test("layer state pushed server-side arrives live over SSE", async ({
  page,
  request,
}) => {
  await request.post(`${BACKEND}/__test__/reset`);
  let loads = 0;
  page.on("load", () => {
    loads += 1;
  });

  let statusRequests = 0;
  await page.route("**/api/status", async (route) => {
    statusRequests += 1;
    await route.continue();
  });

  await signIn(page);
  const bootStatusRequests = statusRequests;
  expect(bootStatusRequests).toBe(1);

  await request.post(`${BACKEND}/__test__/layer`, {
    data: { url: "https://example.com/Pushed", title: "Pushed Layer" },
  });

  await expect(page.getByTestId("layer-row").first()).toContainText(
    "Pushed Layer",
  );
  expect(statusRequests).toBe(bootStatusRequests);
  expect(loads).toBe(1);
});
