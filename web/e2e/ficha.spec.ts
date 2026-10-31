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
  await expect(page.getByTestId("sheet-aspects")).toContainText(
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
  await expect(page.getByTestId("sheet-consequences")).toContainText(
    "Casco rachado",
  );
  await expect(page.getByTestId("sheet-consequences")).toContainText("Livre");
  await expect(page.getByTestId("sheet-extras")).toContainText("Noética");
  await expect(page.getByTestId("sheet-inventory")).toContainText(
    "Espada de Lancelot",
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
  await expect(page.getByTestId("sheet-aspects")).toContainText(
    "Piloto de carga",
  );
});
