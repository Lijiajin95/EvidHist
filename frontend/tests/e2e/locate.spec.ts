import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

async function openTool(page: Page): Promise<void> {
  await page.goto("/");
  await page.getByRole("button", { name: "引文定位工具" }).click();
}

async function fillForm(page: Page, overrides: Partial<Record<string, string>> = {}) {
  const values = {
    version: "史記-001",
    text: "帝曰：甲𠀀乙，命有司封禪。",
    start: "4",
    end: "5",
    quote: "𠀀",
    ...overrides,
  };
  await page.getByLabel("文本版本编号").fill(values.version);
  await page.getByLabel("引文版本编号").fill(values.version);
  await page.getByLabel("文本（本界面只校验此文本）").fill(values.text);
  await page.getByLabel("起点（Unicode 码点，含）").fill(values.start);
  await page.getByLabel("终点（Unicode 码点，不含）").fill(values.end);
  await page.getByLabel("引文", { exact: true }).fill(values.quote);
}

// 材料／论断／引文定位工具视图当前不作为界面入口（主界面只保留对话），
// 浏览器级流程暂时停用；视图恢复入口后删除这段 beforeEach 即可重新启用。
test.beforeEach(() => {
  test.skip(true, "工作台视图当前隐藏，仅对话作为主界面");
});

test("locates a supplementary-plane quote end to end and highlights it", async ({ page }) => {
  await openTool(page);
  await fillForm(page);
  await page.getByRole("button", { name: "校验位置" }).click();

  const result = page.getByTestId("locate-result");
  await expect(result).toContainText("已定位：版本 史記-001，区间 [4, 5)。");
  await expect(page.getByTestId("highlighted-quote")).toHaveText("𠀀");
  await expect(page.getByTestId("source-highlight")).toContainText("帝曰：甲𠀀乙，命有司封禪。");
});

test("a version mismatch is shown as a readable error, not raw JSON", async ({ page }) => {
  await openTool(page);
  await fillForm(page, {});
  await page.getByLabel("引文版本编号").fill("漢書-002");
  await page.getByRole("button", { name: "校验位置" }).click();

  const failure = page.getByTestId("locate-failure");
  await expect(failure).toContainText("版本不符");
  await expect(failure).not.toContainText("{");
});

test("the screen has no serious or critical axe violations", async ({ page }) => {
  await openTool(page);
  await fillForm(page);
  await page.getByRole("button", { name: "校验位置" }).click();
  await expect(page.getByTestId("locate-result")).toBeVisible();

  const results = await new AxeBuilder({ page }).analyze();
  const blocking = results.violations.filter((violation) =>
    ["serious", "critical"].includes(violation.impact ?? ""),
  );
  expect(blocking, JSON.stringify(blocking, null, 2)).toEqual([]);
});

test("keyboard-only users can reach and operate the form", async ({ page }) => {
  await openTool(page);
  await page.keyboard.press("Tab");

  const focused = page.locator(":focus");
  await expect(focused).toBeAttached();
  const focusableCount = await page
    .locator("input, textarea, button")
    .evaluateAll((elements) => elements.filter((element) => element.tabIndex !== -1).length);
  expect(focusableCount).toBeGreaterThanOrEqual(6);
});
