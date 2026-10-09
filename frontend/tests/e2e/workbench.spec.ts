import { expect, test, type Page } from "@playwright/test";

/**
 * Real-browser product flow over the real backend and PostgreSQL: enter a
 * material, keep its immutable version, select a quote in the version text,
 * have the backend validate it against the persisted version, bind it as
 * evidence on a claim together with a second (disagreeing) binding, and read
 * everything back after a full page reload.
 */

function marker(): string {
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
}

async function selectUtf16Range(page: Page, start: number, end: number): Promise<void> {
  await page.getByTestId("version-text").evaluate(
    (element: HTMLTextAreaElement, range: number[]) => {
      element.focus();
      element.setSelectionRange(range[0] ?? 0, range[1] ?? 0);
      element.dispatchEvent(new Event("select", { bubbles: true }));
      document.dispatchEvent(new Event("selectionchange"));
    },
    [start, end],
  );
}

test("材料录入、版本保存、引文校验、论断绑定、多证据与刷新回查", async ({ page }) => {
  const tag = marker();
  const title = `史記·秦始皇本紀（E2E ${tag}）`;
  const statement = `始皇曾東巡封禪（E2E ${tag}）。`;

  await page.goto("/");
  await page.getByRole("button", { name: "添加材料" }).click();
  await page.getByLabel("标题").fill(title);
  await page.getByLabel("来源说明").fill("E2E 合成材料");
  await page.getByLabel("材料使用条件").fill("合成材料，仅演示用途");
  await page.getByLabel("初始版本说明").fill("E2E 初稿");
  await page.getByLabel("初始文本").fill("帝曰：甲𠀀乙𠀀，命有司封禪。");
  await page.getByRole("button", { name: "保存材料" }).click();
  await expect(page.getByText("已保存材料与初始版本。")).toBeVisible();

  await page.getByRole("button", { name: title }).click();
  await expect(page.getByTestId("version-list")).toBeVisible();
  await page.getByRole("button", { name: "E2E 初稿" }).click();
  await expect(page.getByTestId("version-text")).toBeVisible();

  // 𠀀 occupies UTF-16 units 4–6; selecting the whole pair yields code points [4, 5).
  await selectUtf16Range(page, 4, 6);
  await expect(page.getByTestId("selected-quote")).toContainText("已选引文：区间 [4, 5)");
  await page.getByRole("button", { name: "校验位置" }).click();
  await expect(page.getByTestId("verify-ok")).toBeVisible();
  await page.getByRole("button", { name: "用于绑定证据" }).click();

  await expect(page.getByTestId("pending-quote")).toBeVisible();
  await page.getByRole("button", { name: "新建论断" }).first().click();
  await page.getByLabel("论断描述").fill(statement);
  await page.getByRole("button", { name: "保存论断" }).click();
  await expect(page.getByText("已创建论断（默认未核查）。")).toBeVisible();

  await page.getByRole("button", { name: statement }).click();
  await page.getByRole("button", { name: "新增证据绑定" }).click();
  await expect(page.getByTestId("prefilled-quote")).toContainText("区间 [4, 5)");
  await page.getByLabel("关系").selectOption("supports");
  await page.getByLabel("说明").fill("本紀明載（E2E）");
  await page.getByRole("button", { name: "绑定证据" }).click();
  await expect(page.getByTestId("evidence-feedback")).toContainText("已绑定证据。");
  await expect(page.getByTestId("evidence-list")).toContainText("支持");

  // The same quote 𠀀 appears twice; select the second occurrence explicitly —
  // repeated wording resolves by position, never by first-match guessing.
  await page.getByRole("button", { name: "材料" }).click();
  await page.getByRole("button", { name: title }).click();
  await page.getByRole("button", { name: "E2E 初稿" }).click();
  await selectUtf16Range(page, 7, 9);
  await page.getByRole("button", { name: "校验位置" }).click();
  await expect(page.getByTestId("verify-ok")).toBeVisible();
  await page.getByRole("button", { name: "用于绑定证据" }).click();

  await page.getByRole("button", { name: statement }).click();
  await page.getByRole("button", { name: "新增证据绑定" }).click();
  await expect(page.getByTestId("prefilled-quote")).toContainText("区间 [6, 7)");
  await page.getByLabel("关系").selectOption("contradicts");
  await page.getByLabel("说明").fill("另一整理本此處用字不同（E2E）");
  await page.getByRole("button", { name: "绑定证据" }).click();
  await expect(page.getByTestId("evidence-feedback")).toContainText("已绑定证据。");
  await expect(page.getByTestId("evidence-list")).toContainText("反对");
  await expect(page.getByText("核查状态：未核查")).toBeVisible();

  await page.reload();
  await page.getByRole("button", { name: "论断" }).click();
  await page.getByRole("button", { name: statement }).click();
  const evidence = page.getByTestId("evidence-list");
  await expect(evidence).toContainText("𠀀");
  await expect(evidence).toContainText("支持");
  await expect(evidence).toContainText("反对");
  await expect(evidence).toContainText(title);
  await expect(page.getByText("核查状态：未核查")).toBeVisible();
  await expect(page.getByText("该论断还没有绑定证据。")).toHaveCount(0);
});

test("同一材料的重复提交在真实后端下不产生重复业务行", async ({ page }) => {
  const tag = marker();
  const title = `漢書·高帝紀（E2E ${tag}）`;

  await page.goto("/");
  await page.getByRole("button", { name: "添加材料" }).click();
  await page.getByLabel("标题").fill(title);
  await page.getByLabel("来源说明").fill("E2E 合成材料");
  await page.getByLabel("材料使用条件").fill("合成材料，仅演示用途");
  await page.getByLabel("初始版本说明").fill("E2E 初稿");
  await page.getByLabel("初始文本").fill("高祖，沛豐邑中陽里人。");
  await page.getByRole("button", { name: "保存材料" }).click();
  await expect(page.getByText("已保存材料与初始版本。")).toBeVisible();

  await page.getByRole("button", { name: "取消添加" }).click();
  await page.getByRole("button", { name: "添加材料" }).click();
  await page.getByLabel("标题").fill(title);
  await page.getByLabel("来源说明").fill("E2E 合成材料");
  await page.getByLabel("材料使用条件").fill("合成材料，仅演示用途");
  await page.getByLabel("初始版本说明").fill("E2E 初稿");
  await page.getByLabel("初始文本").fill("高祖，沛豐邑中陽里人。");
  await page.getByRole("button", { name: "保存材料" }).click();
  await expect(page.getByText("同题材料已存在，已返回既有材料与初始版本。")).toBeVisible();
  await expect(page.getByRole("button", { name: title })).toHaveCount(1);
});

test("手动绑定越界区间时后端返回可读的 422 错误", async ({ page }) => {
  const tag = marker();
  const title = `越界測試材料（E2E ${tag}）`;
  const statement = `越界論斷（E2E ${tag}）。`;

  await page.goto("/");
  await page.getByRole("button", { name: "添加材料" }).click();
  await page.getByLabel("标题").fill(title);
  await page.getByLabel("来源说明").fill("E2E 合成材料");
  await page.getByLabel("材料使用条件").fill("合成材料，仅演示用途");
  await page.getByLabel("初始版本说明").fill("E2E 初稿");
  await page.getByLabel("初始文本").fill("甲乙丙");
  await page.getByRole("button", { name: "保存材料" }).click();
  await expect(page.getByText("已保存材料与初始版本。")).toBeVisible();

  await page.getByRole("button", { name: "论断" }).click();
  await page.getByRole("button", { name: "新建论断" }).first().click();
  await page.getByLabel("论断描述").fill(statement);
  await page.getByRole("button", { name: "保存论断" }).click();
  await expect(page.getByText("已创建论断（默认未核查）。")).toBeVisible();

  await page.getByRole("button", { name: statement }).click();
  await page.getByRole("button", { name: "新增证据绑定" }).click();
  await page.getByLabel("选择材料").selectOption({ label: title });
  await page.getByLabel("选择版本").selectOption({ label: "E2E 初稿" });
  await page.getByLabel("起点（Unicode 码点，含）").fill("99");
  await page.getByLabel("终点（Unicode 码点，不含）").fill("100");
  await page.getByLabel("引文").fill("甲");
  await page.getByLabel("关系").selectOption("supports");
  await page.getByRole("button", { name: "绑定证据" }).click();

  await expect(page.getByTestId("evidence-feedback")).toContainText("区间无效");
  await expect(page.getByText("已绑定证据。")).toHaveCount(0);
});
