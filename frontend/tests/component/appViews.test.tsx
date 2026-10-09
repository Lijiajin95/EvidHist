import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "../../src/App";
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
 * App-shell integration: navigation between the workbench views and the
 * cross-view flow of selecting a quote in a version, verifying it, and
 * binding it to a claim.
 */

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

describe("workbench shell", () => {
  it("navigates between materials, claims and the locate tool", async () => {
    useWorkbenchHandlers();
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: "材料" }));
    expect(await screen.findByText("史記·秦始皇本紀")).toBeVisible();

    await user.click(screen.getByRole("button", { name: "论断" }));
    expect(await screen.findByText("秦並天下在三十六年。")).toBeVisible();

    await user.click(screen.getByRole("button", { name: "引文定位工具" }));
    expect(await screen.findByText("引用定位工具")).toBeVisible();
  });

  it("carries a selected quote from a version into a claim's evidence binding", async () => {
    useWorkbenchHandlers();
    const user = userEvent.setup();
    render(<App />);

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
    render(<App />);

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
