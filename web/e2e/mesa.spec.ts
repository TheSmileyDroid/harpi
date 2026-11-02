import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

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
