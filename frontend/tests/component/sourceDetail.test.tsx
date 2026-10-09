import { fireEvent, render, screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SourceDetailView } from "../../src/components/sources/SourceDetailView";
import { VersionContentPanel } from "../../src/components/sources/VersionContentPanel";
import { VersionForm } from "../../src/components/sources/VersionForm";
import type { PendingQuote } from "../../src/domain/pendingQuote";
import {
  addVersionExistingHandler,
  addVersionHandler,
  locateVersionHandler,
  locateVersionMismatchHandler,
  sourceDetailHandler,
  sourceNotFoundHandler,
  versionContentHandler,
  versionNotFoundHandler,
} from "../mocks/workbenchHandlers";
import { VERSION_ID } from "../mocks/workbenchFixtures";
import { server } from "../mocks/server";

describe("source detail", () => {
  it("shows the source metadata and its versions", async () => {
    server.use(sourceDetailHandler());
    render(
      <SourceDetailView sourceId="s1" onBack={() => undefined} onUseQuote={() => undefined} />,
    );

    expect(await screen.findByText("史記·秦始皇本紀")).toBeVisible();
    expect(screen.getByText("整理稿一")).toBeVisible();
    expect(screen.getByText(/散列 0123456789ab/)).toBeVisible();
  });

  it("shows a readable error when the source is gone", async () => {
    server.use(sourceNotFoundHandler);
    render(
      <SourceDetailView sourceId="s1" onBack={() => undefined} onUseQuote={() => undefined} />,
    );

    expect(await screen.findByText("材料不存在或已被删除。")).toBeVisible();
  });

  it("reports a source with no versions and reveals the version form", async () => {
    server.use(sourceDetailHandler([]));
    const user = userEvent.setup();
    render(
      <SourceDetailView sourceId="s1" onBack={() => undefined} onUseQuote={() => undefined} />,
    );

    expect(await screen.findByText("该材料还没有文本版本。")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "新增版本" }));
    expect(screen.getByRole("button", { name: "保存版本" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "取消新增版本" }));
    expect(screen.queryByRole("button", { name: "保存版本" })).toBeNull();
  });
});

function selectRange(start: number, end: number) {
  const area = screen.getByTestId<HTMLTextAreaElement>("version-text");
  area.setSelectionRange(start, end);
  fireEvent.select(area);
}

describe("version text selection", () => {
  it("converts a selection of an astral character into the correct code-point range", async () => {
    server.use(versionContentHandler("甲𠀀乙"));
    render(<VersionContentPanel versionId={VERSION_ID} onUseQuote={() => undefined} />);

    await screen.findByTestId("version-text");
    selectRange(1, 3);

    const panel = screen.getByTestId("selected-quote");
    expect(panel).toHaveTextContent("区间 [1, 2)");
    expect(panel).toHaveTextContent("共 1 个 Unicode 码点");
    expect(panel).toHaveTextContent("𠀀");
  });

  it("reports a verified selection and forwards it for evidence binding", async () => {
    server.use(versionContentHandler("帝曰：甲𠀀乙。"), locateVersionHandler);
    const onUseQuote = vi.fn<(quote: PendingQuote) => void>();
    render(<VersionContentPanel versionId={VERSION_ID} onUseQuote={onUseQuote} />);

    await screen.findByTestId("version-text");
    selectRange(4, 6);
    await userEvent.click(screen.getByRole("button", { name: "校验位置" }));

    expect(await screen.findByTestId("verify-ok")).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "用于绑定证据" }));

    expect(onUseQuote).toHaveBeenCalledWith({
      versionId: VERSION_ID,
      versionLabel: "整理稿一",
      start: 4,
      end: 5,
      quote: "𠀀",
    });
  });

  it("shows a readable error when the version content is gone", async () => {
    server.use(versionNotFoundHandler);
    render(<VersionContentPanel versionId={VERSION_ID} onUseQuote={() => undefined} />);

    expect(await screen.findByText("文本版本不存在或已被删除。")).toBeVisible();
  });

  it("shows a readable error when the located wording does not match", async () => {
    server.use(versionContentHandler("甲乙"), locateVersionMismatchHandler);
    render(<VersionContentPanel versionId={VERSION_ID} onUseQuote={() => undefined} />);

    await screen.findByTestId("version-text");
    selectRange(0, 2);
    await userEvent.click(screen.getByRole("button", { name: "校验位置" }));

    expect(await screen.findByTestId("verify-error")).toHaveTextContent("字句不符");
  });
});

describe("version form", () => {
  it("saves a new version and reports it", async () => {
    server.use(addVersionHandler);
    const onSaved = vi.fn();
    const user = userEvent.setup();
    render(<VersionForm sourceId="s1" onSaved={onSaved} />);

    await user.type(screen.getByLabelText("版本说明"), "校勘稿");
    await user.type(screen.getByLabelText("新版本文本"), "新文本");
    await user.click(screen.getByRole("button", { name: "保存版本" }));

    expect(await screen.findByTestId("version-feedback")).toHaveTextContent("已新增版本");
    expect(onSaved).toHaveBeenCalled();
  });

  it("reports identical content as the stored version", async () => {
    server.use(addVersionExistingHandler);
    const user = userEvent.setup();
    render(<VersionForm sourceId="s1" onSaved={() => undefined} />);

    await user.type(screen.getByLabelText("新版本文本"), "相同文本");
    await user.click(screen.getByRole("button", { name: "保存版本" }));

    expect(await screen.findByTestId("version-feedback")).toHaveTextContent("相同文本已有版本");
  });

  it("blocks an empty version submission", async () => {
    const user = userEvent.setup();
    render(<VersionForm sourceId="s1" onSaved={() => undefined} />);

    await user.click(screen.getByRole("button", { name: "保存版本" }));

    expect(await screen.findByTestId("version-feedback")).toHaveTextContent("请填写文本");
  });

  it("shows a readable failure when saving a version cannot reach the service", async () => {
    server.use(http.post("/v1/sources/:id/versions", () => HttpResponse.error()));
    const user = userEvent.setup();
    render(<VersionForm sourceId="s1" onSaved={() => undefined} />);

    await user.type(screen.getByLabelText("新版本文本"), "新文本");
    await user.click(screen.getByRole("button", { name: "保存版本" }));

    expect(await screen.findByTestId("version-feedback")).toHaveTextContent("无法连接服务");
  });
});
