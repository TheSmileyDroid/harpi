import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

const BACKEND = "http://127.0.0.1:8100";
const PAGE = "/c/paratheos/personagens";
const FICHA = "/c/paratheos/ficha";

async function post(page: Page, path: string, data: object = {}) {
  await page.request.post(`${BACKEND}${path}`, { data });
}

async function enroll(page: Page, user: string, name: string, display: string) {
  await post(page, "/__test__/enroll", {
    user_id: user,
    name,
    display_name: display,
    member: true,
  });
}

async function signIn(page: Page, user: string, username = "panel-user") {
  await post(page, "/__test__/login", { user_id: user, username });
}

async function createViaForm(page: Page, name: string, concept: string) {
  await page.getByTestId("character-name").fill(name);
  await page.getByTestId("character-concept").fill(concept);
  await page.getByTestId("character-summary").fill("Veio do porto.");
  await page.getByTestId("character-submit").click();
  await expect(page.getByTestId("cast-error")).toHaveCount(0);
  await expect(page.getByTestId("cast-notice")).toContainText("aprovação");
  await expect(page.getByTestId("cast-pending")).toBeVisible();
}

test("a player creates the pair and the narrator approves it", async ({
  page,
}) => {
  await post(page, "/__test__/reset");
  await enroll(page, "888", "Lia", "Lia Player");
  await signIn(page, "888", "lia");
  await page.goto(PAGE);

  await expect(page.getByTestId("character-create")).toBeVisible();
  await createViaForm(page, "Lia", "Batedora");

  await signIn(page, "555", "harness");
  await page.goto(PAGE);
  const item = page.getByTestId("approval-item").filter({ hasText: "Lia" });
  await expect(item).toBeVisible();
  await expect(item).toContainText("Lia Player");

  await item.getByTestId("approval-approve").click();

  await expect(page.getByTestId("cast-notice")).toContainText("Ficha aprovada");
  await expect(
    page.getByTestId("approval-item").filter({ hasText: "Lia" }),
  ).toHaveCount(0);
  await expect(
    page.getByTestId("cast-card").filter({ hasText: "Lia" }),
  ).toBeVisible();

  await enroll(page, "555", "Cid", "Narrador");
  await page.reload();
  await page.getByTestId("character-name").fill("Cid");
  await page.getByTestId("character-concept").fill("Guardião");
  await page.getByTestId("character-submit").click();

  await expect(page.getByTestId("cast-notice")).toContainText("NPC criado");
  await expect(
    page.getByTestId("cast-card").filter({ hasText: "Cid" }),
  ).toBeVisible();
  await expect(
    page.getByTestId("approval-item").filter({ hasText: "Cid" }),
  ).toHaveCount(0);
});

test("a rejection returns with the note and the owner resubmits", async ({
  page,
}) => {
  await post(page, "/__test__/reset");
  await enroll(page, "889", "Mira", "Mira Player");
  await signIn(page, "889", "mira");
  await page.goto(PAGE);
  await createViaForm(page, "Mira", "Vigia");

  await signIn(page, "555", "harness");
  await page.goto(PAGE);
  const item = page.getByTestId("approval-item").filter({ hasText: "Mira" });
  await item.getByTestId("approval-note").fill("Falta o problema.");
  await item.getByTestId("approval-reject").click();
  await expect(
    page.getByTestId("approval-item").filter({ hasText: "Mira" }),
  ).toHaveCount(0);

  await signIn(page, "889", "mira");
  await page.goto(FICHA);
  await page.getByTestId("sheet-pick").filter({ hasText: "Mira" }).click();

  await expect(page.getByTestId("sheet-review")).toContainText(
    "Falta o problema.",
  );
  await page.getByTestId("sheet-resubmit").click();

  await expect(page.getByTestId("sheet-resubmit-notice")).toContainText(
    "reenviada",
  );
  await expect(page.getByTestId("sheet-review")).toHaveCount(0);

  await signIn(page, "555", "harness");
  await page.goto(PAGE);
  await expect(
    page.getByTestId("approval-item").filter({ hasText: "Mira" }),
  ).toBeVisible();
});
