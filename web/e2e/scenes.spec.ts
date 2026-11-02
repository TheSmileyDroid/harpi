import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

const BACKEND = "http://127.0.0.1:8100";
const PAGE = "/c/paratheos/cenas";

async function signIn(page: Page) {
  await page.request.post(`${BACKEND}/__test__/reset`);
  await page.request.post(`${BACKEND}/__test__/login`);
  await page.goto(PAGE);
}

test("the narrator creates a scene and the gallery shows its card", async ({
  page,
}) => {
  await signIn(page);

  await expect(page.getByTestId("scenes-forbidden")).toHaveCount(0);
  await expect(page.getByTestId("scene-card")).toHaveCount(0);

  await page.getByTestId("scene-new").click();
  await page.getByTestId("scene-name").fill("Cripta");
  await page.getByTestId("scene-image").fill("Arte/ana.png");
  await page.getByTestId("scene-submit").click();

  const card = page.getByTestId("scene-card").filter({ hasText: "Cripta" });
  await expect(card).toBeVisible();
  await expect(card).toContainText("Imagem");
  await expect(card).toContainText("Áreas");
  await expect(card.getByTestId("scene-saved")).toHaveText("Salvo");
  const thumb = card.locator("img");
  await expect(thumb).toHaveAttribute(
    "src",
    /\/api\/campaigns\/paratheos\/scenes\/cripta\/image$/,
  );
  await expect(thumb).toHaveJSProperty("naturalWidth", 1);

  await card.getByTestId("scene-open").click();
  await expect(page.getByTestId("scene-editor")).toBeVisible();
  await expect(page.getByTestId("scene-stage")).toBeVisible();
});

test("a sketch card draws its zones from the blueprint", async ({ page }) => {
  await signIn(page);
  const created = await page.request.post(`${BACKEND}/__test__/scene`, {
    data: {
      name: "Calabouço",
      source: "sketch",
      zones: [
        {
          id: "zon_sala",
          label: "Sala",
          revealed: true,
          rects: [{ x: 0, y: 0, w: 2, h: 2 }],
        },
      ],
    },
  });
  expect(created.status()).toBe(200);

  await page.reload();

  const card = page.getByTestId("scene-card").filter({ hasText: "Calabouço" });
  await expect(card).toBeVisible();
  await expect(card).toContainText("Desenho");
  await expect(card.locator("svg.gallery__preview")).toBeVisible();
  await expect(card.getByTestId("scene-saved")).toHaveText("Salvo");
});

test("the narrator draws a room, deletes it with the keyboard and saves", async ({
  page,
}) => {
  await signIn(page);
  const created = await page.request.post(`${BACKEND}/__test__/scene`, {
    data: {
      name: "Calabouço",
      source: "sketch",
      image_width: 420,
      image_height: 280,
      grid: { cell_px: 70, offset_x: 0, offset_y: 0, visible: true },
      zones: [
        {
          id: "zon_sala",
          label: "Sala",
          revealed: false,
          rects: [{ x: 0, y: 0, w: 1, h: 1 }],
        },
      ],
    },
  });
  expect(created.status()).toBe(200);
  await page.goto(`${PAGE}/calabouco`);

  await expect(page.getByTestId("scene-editor")).toBeVisible();
  await expect(page.getByTestId("scene-usage")).toContainText(
    "Sem mesa · 0 tokens",
  );
  await expect(page.locator(".editor__hidden")).toHaveText("oculta");

  const stage = page.getByTestId("scene-stage");
  const box = await stage.boundingBox();
  expect(box).not.toBeNull();
  if (!box) return;
  await page.keyboard.press("e");
  await expect(page.getByTestId("scene-tool-erase")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await page.keyboard.press("v");
  await expect(page.getByTestId("scene-tool-select")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await page.keyboard.press("r");
  await expect(page.getByTestId("scene-tool-room")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.4);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.75, box.y + box.height * 0.6);
  await page.mouse.up();

  await expect(page.getByTestId("scene-room-key")).toHaveCount(2);

  await page.keyboard.press("v");
  await page.mouse.dblclick(
    box.x + box.width * (35 / 420),
    box.y + box.height * (35 / 280),
  );
  await expect(page.getByTestId("scene-label")).toBeFocused();

  await page.getByTestId("scene-room-key").last().click();
  await page.keyboard.press("Delete");
  await expect(page.getByTestId("scene-room-key")).toHaveCount(1);
  await page.getByTestId("scene-undo").click();
  await expect(page.getByTestId("scene-room-key")).toHaveCount(2);

  const cell = page.getByTestId("scene-cell");
  await cell.fill("35");
  await cell.blur();
  await expect(cell).toHaveValue("35");
  await page.getByTestId("scene-undo").click();
  await expect(cell).toHaveValue("70");

  await page.keyboard.press("s");
  await expect(page.getByTestId("scene-editor-notice")).toHaveText(
    "Cena salva.",
  );

  const map = await page.evaluate(async () => {
    const response = await fetch(
      "/api/campaigns/paratheos/scenes/calabouco/image",
    );
    return {
      status: response.status,
      contentType: response.headers.get("content-type"),
      nosniff: response.headers.get("x-content-type-options"),
      csp: response.headers.get("content-security-policy"),
      body: await response.text(),
    };
  });
  expect(map.status).toBe(200);
  expect(map.contentType).toContain("image/svg+xml");
  expect(map.nosniff).toBe("nosniff");
  expect(map.csp).toBe("sandbox");
  expect(map.body).toContain("<svg");

  await page.reload();
  await expect(page.getByTestId("scene-room-key")).toHaveCount(2);

  await page.getByTestId("scene-room-key").first().click();
  await page.keyboard.press("Delete");
  await page.getByTestId("scene-room-key").first().click();
  await page.keyboard.press("Delete");
  await expect(page.getByTestId("scene-room-key")).toHaveCount(0);
  await page.keyboard.press("s");
  await expect(page.getByTestId("scene-editor-notice")).toHaveText(
    "Cena salva.",
  );
  await page.reload();
  await expect(page.getByTestId("scene-room-key")).toHaveCount(0);
});

test.describe("on a phone", () => {
  test.use({ hasTouch: true, viewport: { width: 390, height: 844 } });

  test("a tap draws a room on the stage", async ({ page }) => {
    await signIn(page);
    const created = await page.request.post(`${BACKEND}/__test__/scene`, {
      data: {
        name: "Calabouço",
        source: "sketch",
        image_width: 420,
        image_height: 280,
        grid: { cell_px: 70, offset_x: 0, offset_y: 0, visible: true },
        zones: [
          {
            id: "zon_sala",
            label: "Sala",
            revealed: false,
            rects: [{ x: 0, y: 0, w: 1, h: 1 }],
          },
        ],
      },
    });
    expect(created.status()).toBe(200);
    await page.goto(`${PAGE}/calabouco`);

    await page.getByTestId("scene-tool-room").click();
    const box = await page.getByTestId("scene-stage").boundingBox();
    expect(box).not.toBeNull();
    if (!box) return;
    await page.touchscreen.tap(
      box.x + box.width * 0.5,
      box.y + box.height * 0.5,
    );

    await expect(page.getByTestId("scene-room-key")).toHaveCount(2);
  });
});

test("a duplicate name is refused without a second card", async ({ page }) => {
  await signIn(page);

  for (const attempt of ["Cripta", "Cripta"]) {
    await page.getByTestId("scene-new").click();
    await page.getByTestId("scene-name").fill(attempt);
    await page.getByTestId("scene-image").fill("Arte/ana.png");
    await page.getByTestId("scene-submit").click();
    if (attempt === "Cripta") {
      await expect(page.getByTestId("scene-card")).toHaveCount(1);
    }
  }

  await expect(page.getByTestId("scenes-error")).toContainText(
    "Já existe uma cena com esse nome.",
  );
  await expect(page.getByTestId("scene-card")).toHaveCount(1);
});
