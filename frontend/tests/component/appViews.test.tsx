import { useCallback, useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ClaimsView } from "../../src/components/claims/ClaimsView";
import { SourcesView } from "../../src/components/sources/SourcesView";
import type { PendingQuote } from "../../src/domain/pendingQuote";
import {
  bindEvidenceHandler,
  claimDetailHandler,
  claimsListHandler,
  locateVersionHandler,
  sourcesListHandler,
  sourceDetailHandler,
  versionContentHandler,
} from "../mocks/workbenchHandlers";
import { server } from "../mocks/server";

/**
 * 工作台视图（材料／论断）当前不作为界面入口（主界面只保留对话），但
 * 「在版本里选中引文 → 带到论断视图绑定证据」仍是产品逻辑。这里用最小外壳
 * 复现该接线，避免这层行为失去覆盖；外壳只存在于测试中。
 */
function WorkbenchHarness() {
  const [pendingQuote, setPendingQuote] = useState<PendingQuote | null>(null);
  const consume = useCallback(() => setPendingQuote(null), []);
  return (
    <>
      <SourcesView onUseQuote={setPendingQuote} />
      <ClaimsView pendingQuote={pendingQuote} onQuoteConsumed={consume} />
    </>
  );
}

function useWorkbenchHandlers() {
  server.use(
    sourcesListHandler,
    sourceDetailHandler(),
    versionContentHandler("帝曰：甲𠀀乙。"),
    locateVersionHandler,
    claimsListHandler,
    claimDetailHandler(),
    bindEvidenceHandler,
  );
}

function selectAstralQuote() {
  const area = screen.getByTestId<HTMLTextAreaElement>("version-text");
  area.setSelectionRange(4, 6);
  fireEvent.select(area);
}

describe("workbench views（当前不作为界面入口）", () => {
  it("carries a selected quote from a version into a claim's evidence binding", async () => {
    useWorkbenchHandlers();
    const user = userEvent.setup();
    render(<WorkbenchHarness />);

    await user.click(await screen.findByText("史記·秦始皇本紀"));
    await user.click(await screen.findByText("整理稿一"));
    await screen.findByTestId("version-text");
    selectAstralQuote();
    await user.click(screen.getByRole("button", { name: "校验位置" }));
    await screen.findByTestId("verify-ok");
    await user.click(screen.getByRole("button", { name: "用于绑定证据" }));

    const banner = await screen.findByTestId("pending-quote");
    expect(banner).toHaveTextContent("整理稿一");
    expect(banner).toHaveTextContent("区间 [4, 5)");
    expect(banner).toHaveTextContent("𠀀");

    await user.click(screen.getByText("秦並天下在三十六年。"));
    await user.click(await screen.findByRole("button", { name: "新增证据绑定" }));
    expect(screen.getByTestId("prefilled-quote")).toHaveTextContent("区间 [4, 5)");
    await user.selectOptions(screen.getByLabelText("关系"), "supports");
    await user.click(screen.getByRole("button", { name: "绑定证据" }));

    expect(await screen.findByTestId("evidence-feedback")).toHaveTextContent("已绑定证据");
    await screen.findByTestId("evidence-list");
  });

  it("discards a pending quote from the claims view banner", async () => {
    useWorkbenchHandlers();
    const user = userEvent.setup();
    render(<WorkbenchHarness />);

    await user.click(await screen.findByText("史記·秦始皇本紀"));
    await user.click(await screen.findByText("整理稿一"));
    await screen.findByTestId("version-text");
    selectAstralQuote();
    await user.click(screen.getByRole("button", { name: "校验位置" }));
    await screen.findByTestId("verify-ok");
    await user.click(screen.getByRole("button", { name: "用于绑定证据" }));

    await user.click(await screen.findByRole("button", { name: "放弃该引文" }));
    expect(screen.queryByTestId("pending-quote")).toBeNull();
    await screen.findByText("秦並天下在三十六年。");
  });
});
