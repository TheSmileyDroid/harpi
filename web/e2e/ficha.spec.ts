import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

const BACKEND = "http://127.0.0.1:8100";
const FICHA = "/c/paratheos/ficha";

async function signIn(page: Page) {
  await page.request.post(`${BACKEND}/__test__/reset`);
  await page.request.post(`${BACKEND}/__test__/login`);
}

test("the owner reads the whole sheet", async ({ page }) => {
  await signIn(page);
  await page.goto(`${FICHA}/chr_ana`);

  const sheet = page.getByTestId("sheet");
  await expect(sheet).toBeVisible();
  await expect(page.getByTestId("sheet-status")).toHaveText("Ativa");
  await expect(page.getByTestId("sheet-aspect-text").first()).toHaveValue(
    "Piloto de carga",
  );
  await expect(
    page.getByTestId("sheet-aspects").locator(".sheet__aspect"),
  ).toHaveCount(5);
  await expect(
    page.getByTestId("sheet-stunts").locator(".sheet__stunt"),
  ).toHaveCount(2);
  await expect(
    page.getByTestId("sheet-extras").locator(".sheet__extra"),
  ).toHaveCount(2);
  await expect(
    page.getByTestId("sheet-inventory").locator(".sheet__item"),
  ).toHaveCount(2);
  await expect(page.getByTestId("sheet-skills")).toContainText("Ótimo +4");
  await expect(page.getByTestId("sheet-skills")).toContainText("Hackear");
  await expect(page.getByTestId("sheet-skills")).toContainText("Bom +3");
  await expect(page.getByTestId("sheet-stress")).toContainText("Físico");
  await expect(page.getByTestId("sheet-consequence-text").first()).toHaveValue(
    "Casco rachado",
  );
  await expect(page.getByTestId("sheet-consequence-text").nth(1)).toHaveValue(
    "",
  );
  await expect(page.getByTestId("sheet-extras")).toContainText("Noética");
  await expect(page.getByTestId("sheet-extra-name").first()).toHaveValue(
    "Constructo",
  );
  await expect(page.getByTestId("sheet-inventory-item").first()).toHaveValue(
    "[[Espada de Lancelot]]",
  );
  await expect(page.getByTestId("sheet-pending")).toHaveCount(0);
  await expect(page.getByTestId("sheet-readonly")).toHaveCount(0);
});

test("an archived sheet stays read-only", async ({ page }) => {
  await signIn(page);
  await page.goto(`${FICHA}/chr_eva`);

  await expect(page.getByTestId("sheet-status")).toHaveText("Arquivada");
  await expect(page.getByTestId("sheet-readonly")).toBeVisible();
});

test("broken YAML shows the error and locks the sheet", async ({ page }) => {
  await signIn(page);
  await page.goto(`${FICHA}/chr_quebrado`);

  await expect(page.getByTestId("sheet-error")).toBeVisible();
  await expect(page.getByTestId("sheet-readonly")).toBeVisible();
  await expect(page.getByTestId("sheet-aspects")).not.toContainText(
    "Piloto de carga",
  );
});

test("the page lists the visible cast before a sheet is chosen", async ({
  page,
}) => {
  await signIn(page);
  await page.goto(FICHA);

  await expect(page.getByTestId("sheet")).toContainText("Ana");
  await expect(page.getByTestId("sheet")).not.toContainText("Velho");
});

test("the cast links to the sheet page", async ({ page }) => {
  await signIn(page);
  await page.goto("/c/paratheos/personagens");

  const ana = page.getByTestId("cast-card").filter({ hasText: "Ana" });
  await ana.getByTestId("cast-open").click();

  await expect(page).toHaveURL(/\/c\/paratheos\/ficha\/chr_ana$/);
  await expect(page.getByTestId("sheet-aspect-text").first()).toHaveValue(
    "Piloto de carga",
  );
});

test("a stale base hash keeps the draft and locks the sheet", async ({
  page,
}) => {
  await signIn(page);
  await page.goto(`${FICHA}/chr_ana`);
  await page.route("**/sheets/sht_ana", async (route) => {
    if (route.request().method() === "PATCH") {
      await route.fulfill({
        status: 409,
        contentType: "application/json",
        body: JSON.stringify({
          error: { code: "sheet_conflict", message: "Sheet changed on disk" },
        }),
      });
      return;
    }
    await route.continue();
  });

  await page.getByTestId("sheet-aspect-text").first().fill("Rascunho local");
  await page.getByTestId("sheet-save").click();

  await expect(page.getByTestId("sheet-conflict")).toBeVisible();
  await expect(page.getByTestId("sheet-aspect-text").first()).toHaveValue(
    "Rascunho local",
  );
  await expect(page.getByTestId("sheet-save")).toBeDisabled();
});

test("the owner edits the sheet and reloads the new values", async ({
  page,
}) => {
  await signIn(page);
  await page.goto(`${FICHA}/chr_ana`);

  await page.getByLabel("Físico 2 livre").click();
  await page
    .getByTestId("sheet-aspect-text")
    .first()
    .fill("Piloto da nova era");
  await page.getByTestId("sheet-consequence-text").first().fill("Machucado");
  await page.getByTestId("sheet-inventory-item").first().fill("Corda");
  await page.getByTestId("sheet-prose-history").fill("Nova história.");
  await page.getByTestId("sheet-save").click();

  await expect(page.getByTestId("sheet-notice")).toContainText("Ficha salva");
  await page.reload();

  await expect(page.getByLabel("Físico 2 marcada")).toBeVisible();
  await expect(page.getByTestId("sheet-aspect-text").first()).toHaveValue(
    "Piloto da nova era",
  );
  await expect(page.getByTestId("sheet-consequence-text").first()).toHaveValue(
    "Machucado",
  );
  await expect(page.getByTestId("sheet-inventory-item").first()).toHaveValue(
    "[[Corda]]",
  );
  await expect(page.getByTestId("sheet-prose-history")).toHaveValue(
    "Nova história.",
  );
});
