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
