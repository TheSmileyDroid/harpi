import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

const BACKEND = "http://127.0.0.1:8100";
const PAGE = "/c/paratheos/personagens";

async function signIn(page: Page) {
  await page.request.post(`${BACKEND}/__test__/reset`);
  await page.request.post(`${BACKEND}/__test__/login`);
  await page.goto(PAGE);
}

test("the cast shows an active character with the portrait from the vault", async ({
  page,
}) => {
  await signIn(page);

  const ana = page.getByTestId("cast-card").filter({ hasText: "Ana" });
  await expect(ana).toBeVisible();
  await expect(ana).toContainText("Piloto de carga");
  await expect(ana).toContainText("Mensageira sem memória.");

  const portrait = ana.locator("img");
  await expect(portrait).toHaveAttribute(
    "src",
    /\/api\/campaigns\/paratheos\/characters\/chr_ana\/portrait$/,
  );
  await expect(portrait).toHaveJSProperty("naturalWidth", 1);
});

test("an archived character stays out of the cast", async ({ page }) => {
  await signIn(page);

  await expect(page.getByTestId("cast-card").first()).toBeVisible();
  await expect(
    page.getByTestId("cast-card").filter({ hasText: "Velho" }),
  ).toHaveCount(0);
});
