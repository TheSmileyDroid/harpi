import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

const BACKEND = "http://127.0.0.1:8100";

const TWO_COLUMN_MIN = 896;
const COMPACT_CHROME_MAX = 480;

type Resolution = { label: string; width: number; height: number };

const RESOLUTIONS: Resolution[] = [
  { label: "VGA 640x480", width: 640, height: 480 },
  { label: "SVGA 800x600", width: 800, height: 600 },
  { label: "wrap edge 767x900", width: 767, height: 900 },
  { label: "wrap edge 769x900", width: 769, height: 900 },
  { label: "netbook 1024x600", width: 1024, height: 600 },
  { label: "XGA 1024x768", width: 1024, height: 768 },
  { label: "HD 1280x720", width: 1280, height: 720 },
  { label: "laptop 1366x768", width: 1366, height: 768 },
  { label: "MacBook Air 1440x900", width: 1440, height: 900 },
  { label: "tablet landscape 1280x800", width: 1280, height: 800 },
  { label: "tablet portrait 768x1024", width: 768, height: 1024 },
  { label: "iPad Pro portrait 1024x1366", width: 1024, height: 1366 },
  { label: "full HD 1920x1080", width: 1920, height: 1080 },
  { label: "QHD 2560x1440", width: 2560, height: 1440 },
  { label: "ultrawide 3440x1440", width: 3440, height: 1440 },
  { label: "4K 3840x2160", width: 3840, height: 2160 },
  { label: "super ultrawide 5120x1440", width: 5120, height: 1440 },
  { label: "legacy phone 320x480", width: 320, height: 480 },
  { label: "small phone 320x568", width: 320, height: 568 },
  { label: "phone 360x640", width: 360, height: 640 },
  { label: "phone 390x844", width: 390, height: 844 },
  { label: "large phone 412x915", width: 412, height: 915 },
  { label: "compact edge 480x800", width: 480, height: 800 },
  { label: "compact edge 481x800", width: 481, height: 800 },
  { label: "phone landscape 844x390", width: 844, height: 390 },
  { label: "two-column edge 895x900", width: 895, height: 900 },
  { label: "two-column edge 896x900", width: 896, height: 900 },
];

async function boxOf(page: Page, selector: string) {
  const box = await page.locator(selector).boundingBox();
  if (!box) throw new Error(`${selector} has no bounding box`);
  return box;
}

async function expectNoHorizontalOverflow(page: Page, label: string) {
  const measure = await page.evaluate(() => ({
    viewport: window.innerWidth,
    document:
      document.scrollingElement?.scrollWidth ??
      document.documentElement.scrollWidth,
    body: document.body.scrollWidth,
  }));
  expect(
    measure.document,
    `${label}: document scrolls ${measure.document}px wide in ${measure.viewport}px`,
  ).toBeLessThanOrEqual(measure.viewport + 1);
  expect(
    measure.body,
    `${label}: body scrolls ${measure.body}px wide in ${measure.viewport}px`,
  ).toBeLessThanOrEqual(measure.viewport + 1);
}

async function expectTransportContentsFit(page: Page, label: string) {
  const dock = await boxOf(page, "[data-testid='transport']");
  const children = page.locator("[data-testid='transport'] > *");
  const count = await children.count();
  for (let index = 0; index < count; index += 1) {
    const box = await children.nth(index).boundingBox();
    if (!box) continue;
    const name = `${label}: transport child ${index}`;
    expect(box.x, `${name} left edge`).toBeGreaterThanOrEqual(dock.x - 1);
    expect(box.x + box.width, `${name} right edge`).toBeLessThanOrEqual(
      dock.x + dock.width + 1,
    );
    expect(box.y, `${name} top edge`).toBeGreaterThanOrEqual(dock.y - 1);
    expect(box.y + box.height, `${name} bottom edge`).toBeLessThanOrEqual(
      dock.y + dock.height + 1,
    );
  }
}

async function expectInsideViewport(
  page: Page,
  selector: string,
  label: string,
) {
  const box = await boxOf(page, selector);
  const viewport = page.viewportSize();
  if (!viewport) throw new Error("page has no viewport");
  const name = `${label} ${selector}`;
  expect(box.x, `${name}: left edge`).toBeGreaterThanOrEqual(-1);
  expect(box.x + box.width, `${name}: right edge`).toBeLessThanOrEqual(
    viewport.width + 1,
  );
  expect(box.y, `${name}: top edge`).toBeGreaterThanOrEqual(-1);
  expect(box.y + box.height, `${name}: bottom edge`).toBeLessThanOrEqual(
    viewport.height + 1,
  );
}

for (const { label, width, height } of RESOLUTIONS) {
  test(`layout holds at ${label}`, async ({ page }) => {
    await page.request.post(`${BACKEND}/__test__/reset`);
    await page.setViewportSize({ width, height });
    await page.goto("/");

    await expect(page.getByTestId("signin")).toBeVisible();
    await expectInsideViewport(page, "[data-testid='signin-panel']", label);
    await expectNoHorizontalOverflow(page, `${label} sign-in`);

    await page.request.post(`${BACKEND}/__test__/login`);
    await page.reload();
    await expect(page.getByTestId("bot-status")).toHaveText("ONLINE");

    await expectNoHorizontalOverflow(page, `${label} console`);
    await expectInsideViewport(page, "[data-testid='open-search']", label);
    await expectInsideViewport(page, "[data-testid='sign-out']", label);

    const transport = await boxOf(page, "[data-testid='transport']");
    expect(transport.x, `${label}: transport left edge`).toBeLessThanOrEqual(1);
    expect(
      Math.abs(transport.width - width),
      `${label}: transport spans ${transport.width}px of ${width}px`,
    ).toBeLessThanOrEqual(1);
    expect(
      Math.abs(transport.y + transport.height - height),
      `${label}: transport bottom sits ${transport.y + transport.height}px into ${height}px`,
    ).toBeLessThanOrEqual(1);
    await expectTransportContentsFit(page, label);

    const main = await boxOf(page, "[data-testid='console-main']");
    const rail = await boxOf(page, "[data-testid='console-rail']");
    if (width >= TWO_COLUMN_MIN) {
      expect(
        rail.x,
        `${label}: rail is beside the main column`,
      ).toBeGreaterThan(main.x);
      expect(rail.y, `${label}: rail shares the main column row`).toBeLessThan(
        main.y + main.height,
      );
    } else {
      expect(
        rail.y,
        `${label}: rail stacks under the main column`,
      ).toBeGreaterThanOrEqual(main.y + main.height - 1);
    }

    const strip = page.getByTestId("status-strip");
    const readout = page.getByTestId("progress-readout");
    await expect(
      readout,
      `${label}: ready session renders a readout`,
    ).toHaveCount(1);
    if (width <= COMPACT_CHROME_MAX) {
      await expect(strip, `${label}: status strip is dropped`).toBeHidden();
      await expect(readout, `${label}: readout is dropped`).toBeHidden();
    } else {
      await expect(strip, `${label}: status strip is kept`).toBeVisible();
      await expect(readout, `${label}: readout is kept`).toBeVisible();
    }

    await page.evaluate(() =>
      window.scrollTo(0, document.documentElement.scrollHeight),
    );
    const clearance = await page.evaluate(() => {
      const dock = document
        .querySelector("[data-testid='transport']")!
        .getBoundingClientRect();
      const content = document
        .querySelector("[data-testid='console']")!
        .getBoundingClientRect();
      return dock.top - content.bottom;
    });
    expect(
      clearance,
      `${label}: content leaves ${clearance}px above the dock`,
    ).toBeGreaterThanOrEqual(16);
  });
}
