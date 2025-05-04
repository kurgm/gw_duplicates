import { test, expect } from "@playwright/test";

const TOTAL_COUNT = 9;
const TOTAL_TEXT = `の dump より生成（全 ${TOTAL_COUNT} 件）`;
const LOADING_TEXT = "準備中...";
const PLACEHOLDER_TEXT = "検索（グリフ名または漢字）";

const filteredText = (count: number) =>
  `の dump より生成（全 ${TOTAL_COUNT} 件中 ${count} 件を表示）`;

test("has glyph images", async ({ page }) => {
  await page.goto("http://localhost:3000/viewer/");

  // Ensure that the page has loaded.
  await expect(page.getByText(TOTAL_TEXT)).toBeVisible();
  await expect(page.getByText(LOADING_TEXT)).not.toBeVisible();

  await expect(page.getByAltText("u4e00").first()).toBeVisible();
  await expect(page.getByAltText("u4e01").first()).toBeVisible();

  const popupPromise = page.waitForEvent("popup");
  await page.getByAltText("u4e00").first().click();
  const popup = await popupPromise;
  await popup.waitForLoadState();
  await expect(popup).toHaveTitle("u4e00");
  await popup.close();
});

test("has text link", async ({ page }) => {
  await page.goto("http://localhost:3000/viewer/");

  // Ensure that the page has loaded.
  await expect(page.getByText(TOTAL_TEXT)).toBeVisible();
  await expect(page.getByText(LOADING_TEXT)).not.toBeVisible();

  await expect(page.getByText("u4e00").first()).toBeVisible();

  const popupPromise = page.waitForEvent("popup");
  await page.getByText("u4e00").first().click();
  const popup = await popupPromise;
  await popup.waitForLoadState();
  await expect(popup).toHaveTitle("u4e00");
  await popup.close();
});

test("has search box", async ({ page }) => {
  await page.goto("http://localhost:3000/viewer/");

  // Ensure that the page has loaded.
  await expect(page.getByText(TOTAL_TEXT)).toBeVisible();
  await expect(page.getByText(LOADING_TEXT)).not.toBeVisible();

  await expect(page.getByPlaceholder(PLACEHOLDER_TEXT)).toBeVisible();

  await page.getByPlaceholder(PLACEHOLDER_TEXT).fill("u4");
  await expect(page.getByText(filteredText(4))).toBeVisible();

  await page.getByPlaceholder(PLACEHOLDER_TEXT).fill("j1-");
  await expect(page.getByText(filteredText(2))).toBeVisible();
  await expect(page.getByText("u4e00")).not.toBeVisible();

  await page.getByPlaceholder(PLACEHOLDER_TEXT).fill("01$");
  await expect(page.getByText(filteredText(7))).toBeVisible();

  await page.getByPlaceholder(PLACEHOLDER_TEXT).fill("A");
  await expect(page.getByText(filteredText(0))).toBeVisible();
  await expect(page.locator(".table-row")).not.toBeVisible();

  await page.getByPlaceholder(PLACEHOLDER_TEXT).fill("(");
  await expect(page.locator("input:invalid")).toBeVisible();

  await page.getByPlaceholder(PLACEHOLDER_TEXT).fill("\u4e00");
  await expect(page.getByText(filteredText(3))).toBeVisible();

  await page.getByPlaceholder(PLACEHOLDER_TEXT).fill("\u{20000}");
  await expect(page.getByText(filteredText(1))).toBeVisible();
});

test("has edit links", async ({ page }) => {
  await page.goto("http://localhost:3000/viewer/");

  // Ensure that the page has loaded.
  await expect(page.getByText(TOTAL_TEXT)).toBeVisible();
  await expect(page.getByText(LOADING_TEXT)).not.toBeVisible();

  {
    const popupPromise = page.waitForEvent("popup");
    await page.getByText("エイリアス化").first().click();
    const popup = await popupPromise;
    await popup.waitForLoadState();
    await expect(popup).toHaveTitle("Editing u4e00");
    await expect(popup.getByLabel("related")).toHaveValue("u4e00");
    await expect(popup.getByLabel("textbox")).toHaveValue("[[u4e01]]");
    await popup.close();
  }

  {
    const popupPromise = page.waitForEvent("popup");
    await page.getByText("白紙化").first().click();
    const popup = await popupPromise;
    await popup.waitForLoadState();
    await expect(popup).toHaveTitle("Editing u4e00");
    await expect(popup.getByLabel("textbox")).toHaveValue("0:0:0:0");
    await popup.close();
  }

  await page.getByPlaceholder(PLACEHOLDER_TEXT).fill("aj1-00001");

  {
    const popupPromise = page.waitForEvent("popup");
    await page.getByText("エイリアス化").nth(1).click();
    const popup = await popupPromise;
    await popup.waitForLoadState();
    await expect(popup).toHaveTitle("Editing aj1-00001");
    await expect(popup.getByLabel("related")).toHaveValue("u3013");
    await expect(popup.getByLabel("textbox")).toHaveValue("[[aj1-00000]]");
    await popup.close();
  }

  {
    const popupPromise = page.waitForEvent("popup");
    await page.getByText("白紙化").nth(1).click();
    const popup = await popupPromise;
    await popup.waitForLoadState();
    await expect(popup).toHaveTitle("Editing aj1-00001");
    await expect(popup.getByLabel("textbox")).toHaveValue("0:0:0:0");
    await popup.close();
  }
});
