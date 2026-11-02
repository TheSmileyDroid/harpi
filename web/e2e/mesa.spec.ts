import { expect, test } from "@playwright/test";
import type { BrowserContext, Page } from "@playwright/test";

const BACKEND = "http://127.0.0.1:8100";
const MESA = "/c/paratheos/mesa";

async function signIn(page: Page) {
  await page.request.post(`${BACKEND}/__test__/reset`);
  await page.request.post(`${BACKEND}/__test__/login`);
}

async function seedScene(page: Page) {
  const response = await page.request.post(`${BACKEND}/__test__/scene`, {
    data: {
      name: "Cripta",
      source: "image",
      image: "Arte/ana.png",
      fog_outside: true,
      zones: [
        {
          id: "zon_sala",
          label: "Sala principal",
          revealed: false,
          rects: [{ x: 0, y: 0, w: 1, h: 1 }],
        },
      ],
    },
  });
  expect(response.status()).toBe(200);
}

test("the narrator opens the table, adds a token and reveals a zone", async ({
  page,
}) => {
  await signIn(page);
  await seedScene(page);
  await page.goto(MESA);

  await expect(page.getByTestId("table-open-form")).toBeVisible();
  await page.getByTestId("table-open-channel").fill("123456789012345678");
  await page.getByTestId("table-open-name").fill("Sessão 12");
  await page.getByTestId("table-open-submit").click();

  await expect(page.getByTestId("table-summary")).toBeVisible();
  await expect(page.getByTestId("table-status")).toHaveText("Aberta");
  await expect(page.getByTestId("table-round")).toHaveText("Rodada 1");
  await expect(page.getByTestId("table-channel")).toHaveText(
    "123456789012345678",
  );
  await expect(page.getByTestId("table-scene-name")).toHaveText("Cripta");

  await page.getByTestId("map-zone-zon_sala").click();
  await expect(page.getByTestId("table-notice")).toHaveText("Área revelada.");

  await page.getByTestId("table-token-label").fill("Ana");
  await page.getByTestId("table-token-submit").click();
  const token = page.locator('[data-testid^="table-token-tok_"]');
  await expect(token).toHaveCount(1);

  await token.first().click();
  await expect(page.getByTestId("table-drawer")).toBeVisible();
  await expect(page.getByTestId("table-drawer")).toContainText("Ana");
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("table-drawer")).toHaveCount(0);
});

test("closing writes the snapshot and reopening restores the table", async ({
  page,
}) => {
  await signIn(page);
  await seedScene(page);
  await page.goto(MESA);
  await page.getByTestId("table-open-channel").fill("123456789012345678");
  await page.getByTestId("table-open-submit").click();
  await expect(page.getByTestId("table-summary")).toBeVisible();

  await page.getByTestId("table-close").click();
  await expect(page.getByTestId("table-status")).toHaveText("Fechada");
  await expect(page.getByTestId("table-reopen")).toBeVisible();

  await page.getByTestId("table-reopen").click();
  await expect(page.getByTestId("table-status")).toHaveText("Aberta");
  await expect(page.getByTestId("table-close")).toBeVisible();
});

test("the narrator runs a round with a turn", async ({ page }) => {
  await signIn(page);
  await seedScene(page);
  await page.goto(MESA);
  await page.getByTestId("table-open-channel").fill("123456789012345678");
  await page.getByTestId("table-open-submit").click();
  await expect(page.getByTestId("table-summary")).toBeVisible();

  await page.getByTestId("map-zone-zon_sala").click();
  for (const label of ["Ana", "Bob"]) {
    await page.getByTestId("table-token-label").fill(label);
    await page.getByTestId("table-token-submit").click();
  }
  await expect(page.getByTestId("table-turn-state")).toHaveText(
    "Sem turno aberto.",
  );

  await page.getByRole("button", { name: "Abrir turno de Ana" }).click();
  await expect(page.getByTestId("table-turn-state")).toHaveText(
    "Em turno: Ana",
  );

  await page.getByTestId("table-token-label").fill("Cid");
  await page.keyboard.press("n");
  await expect(page.getByTestId("table-turn-state")).toHaveText(
    "Em turno: Ana",
  );

  await page.getByRole("heading", { name: "Turno" }).click();
  await page.keyboard.press("n");
  await expect(page.getByTestId("table-turn-state")).toHaveText(
    "Em turno: Bob",
  );

  await page.getByTestId("table-turn-end").click();
  await expect(page.getByTestId("table-round")).toHaveText("Rodada 2");
  await expect(page.getByTestId("table-turn-state")).toHaveText(
    "Sem turno aberto.",
  );
  await expect(page.getByTestId("table-turn-end")).toHaveCount(0);
});

test("the map stays scrollable with a zoom on a phone", async ({ page }) => {
  await signIn(page);
  await seedScene(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(MESA);
  await page.getByTestId("table-open-channel").fill("123456789012345678");
  await page.getByTestId("table-open-submit").click();

  await expect(page.getByTestId("table-map-viewport")).toBeVisible();
  await page.getByTestId("map-zoom-in").click();
  await expect(page.getByTestId("map-fit")).toBeVisible();
});

async function loginContext(context: BrowserContext): Promise<void> {
  await context.request.post(`${BACKEND}/__test__/login`);
}

async function seedWideScene(page: Page) {
  const response = await page.request.post(`${BACKEND}/__test__/scene`, {
    data: {
      name: "Cripta",
      source: "sketch",
      image_width: 800,
      image_height: 600,
      fog_outside: false,
      zones: [
        {
          id: "zon_sala",
          label: "Sala principal",
          revealed: true,
          rects: [{ x: 0, y: 0, w: 12, h: 9 }],
        },
      ],
    },
  });
  expect(response.status()).toBe(200);
}

async function openTable(page: Page): Promise<string> {
  await page.goto(MESA);
  await page.getByTestId("table-open-channel").fill("123456789012345678");
  await page.getByTestId("table-open-submit").click();
  await expect(page.getByTestId("table-summary")).toBeVisible();
  return page.evaluate(async () => {
    const response = await fetch("/api/campaigns/paratheos");
    const payload = (await response.json()) as {
      open_table: { id: string } | null;
    };
    return payload.open_table?.id ?? "";
  });
}

async function addToken(page: Page, label: string): Promise<string> {
  await page.getByTestId("table-token-label").fill(label);
  await page.getByTestId("table-token-submit").click();
  const token = page.locator('[data-testid^="table-token-tok_"]').last();
  await expect(token).toBeVisible();
  const testId = await token.getAttribute("data-testid");
  return testId!.replace("table-token-", "");
}

async function tokenPosition(
  page: Page,
  tableId: string,
  tokenId: string,
): Promise<{ id: string; x: number; y: number }> {
  return page.evaluate(
    async ({ tableId, tokenId }) => {
      const response = await fetch(`/api/tables/${tableId}/summary`);
      const payload = (await response.json()) as {
        tokens: { id: string; x: number; y: number }[];
      };
      return payload.tokens.find((item) => item.id === tokenId)!;
    },
    { tableId, tokenId },
  );
}

test("two browsers converge on a dragged token", async ({ browser }) => {
  const first = await browser.newContext();
  const second = await browser.newContext();
  const pageA = await first.newPage();
  const pageB = await second.newPage();
  await signIn(pageA);
  await seedWideScene(pageA);
  const tableId = await openTable(pageA);
  const tokenId = await addToken(pageA, "Ana");

  await loginContext(second);
  await pageB.goto(MESA);
  await expect(pageB.getByTestId(`table-token-${tokenId}`)).toBeVisible();
  const before = (await pageB
    .getByTestId(`table-token-${tokenId}`)
    .boundingBox())!;

  const token = pageA.getByTestId(`table-token-${tokenId}`);
  await token.scrollIntoViewIfNeeded();
  const box = (await token.boundingBox())!;
  await pageA.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await pageA.mouse.down();
  await pageA.mouse.move(box.x + box.width / 2 + 140, box.y + box.height / 2, {
    steps: 8,
  });
  await expect(pageB.getByTestId(`table-drag-${tokenId}`)).toBeVisible();
  await pageA.mouse.up();

  await expect
    .poll(async () => {
      const moved = (await pageB
        .getByTestId(`table-token-${tokenId}`)
        .boundingBox())!;
      return moved.x - before.x;
    })
    .toBeGreaterThan(20);
  const placed = await tokenPosition(pageA, tableId, tokenId);
  expect(placed.x).toBeGreaterThan(0);
  await expect(pageB.getByTestId(`table-drag-${tokenId}`)).toHaveCount(0);
  await first.close();
  await second.close();
});

test("the keyboard moves the focused token by one cell and by five", async ({
  page,
}) => {
  await signIn(page);
  await seedWideScene(page);
  const tableId = await openTable(page);
  const tokenId = await addToken(page, "Ana");
  const token = page.getByTestId(`table-token-${tokenId}`);
  const start = await tokenPosition(page, tableId, tokenId);

  await token.focus();
  await page.keyboard.press("ArrowRight");
  await expect
    .poll(async () => (await tokenPosition(page, tableId, tokenId)).x)
    .toBe(start.x + 1);

  await page.keyboard.press("ArrowRight");
  await page.keyboard.press("ArrowRight");
  await expect
    .poll(async () => (await tokenPosition(page, tableId, tokenId)).x)
    .toBe(start.x + 3);

  await page.keyboard.press("Shift+ArrowRight");
  await expect
    .poll(async () => (await tokenPosition(page, tableId, tokenId)).x)
    .toBe(start.x + 8);
});
