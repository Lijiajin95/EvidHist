import { expect, test } from "@playwright/test";

/**
 * 真实浏览器里的对话闭环：主界面只保留对话，拿一份合成材料新建会话并提问，
 * 假 PI（e2e 后端固定使用）走完检索 → 流式回答 → 引文校验，引文以只读卡片
 * 呈现出处与校验结果。断言只看用户可见结果，不依赖真实模型。
 */

function marker(): string {
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
}

test("对话：新建会话、提问、工具卡片、流式回答与引文跳转", async ({ page, request }) => {
  const tag = marker();
  const created = await request.post("/v1/sources", {
    data: {
      title: `于謙守禦（E2E ${tag}）`,
      origin: "E2E 合成材料",
      usage_terms: "合成材料，仅演示用途",
      initial_text: "于謙請駐兵居庸，寇來則出關勦殺，退則就糧京師。",
      initial_label: "E2E 初稿",
    },
  });
  expect(created.ok()).toBeTruthy();

  await page.goto("/");
  await page.getByRole("button", { name: "开启新对话" }).click();

  const composer = page.getByLabel("输入消息");
  await composer.fill("于謙在守禦中的作用是什麼?");
  await composer.press("Enter");

  await expect(page.getByRole("heading", { name: "结论" })).toBeVisible();
  await expect(page.getByText(/search · 命中 \d+ 处/)).toBeVisible();

  const citation = page.locator(".chat-citation").first();
  await expect(citation).toBeVisible();
  await expect(citation).toContainText(/通过程序校验|quote_mismatch/);

  // 主界面只有对话：材料／论断／引文定位工具入口都不应出现
  for (const hidden of ["材料", "论断", "引文定位工具"]) {
    await expect(page.getByRole("button", { name: hidden, exact: true })).toHaveCount(0);
  }
});
