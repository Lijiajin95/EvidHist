import { render, screen, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SourceForm } from "../../src/components/sources/SourceForm";
import { SourceListView } from "../../src/components/sources/SourceListView";
import {
  createSourceExistingHandler,
  createSourceHandler,
  networkFailureSourcesHandler,
  sourcesListHandler,
} from "../mocks/workbenchHandlers";
import { server } from "../mocks/server";

describe("source form", () => {
  it("blocks submission when required fields are missing", async () => {
    const user = userEvent.setup();
    render(<SourceForm onSaved={() => undefined} />);

    await user.click(screen.getByRole("button", { name: "保存材料" }));

    expect(await screen.findByTestId("source-feedback")).toHaveTextContent("请填写标题和初始文本");
  });

  it("saves a material and reports success", async () => {
    server.use(createSourceHandler);
    const onSaved = vi.fn();
    const user = userEvent.setup();
    render(<SourceForm onSaved={onSaved} />);

    await user.type(screen.getByLabelText("标题"), "漢書·藝文志");
    await user.type(screen.getByLabelText("初始文本"), "漢興，改秦之敗。");
    await user.click(screen.getByRole("button", { name: "保存材料" }));

    expect(await screen.findByTestId("source-feedback")).toHaveTextContent("已保存材料与初始版本");
    expect(onSaved).toHaveBeenCalled();
  });

  it("reports an idempotent retry as existing instead of an error", async () => {
    server.use(createSourceExistingHandler);
    const user = userEvent.setup();
    render(<SourceForm onSaved={() => undefined} />);

    await user.type(screen.getByLabelText("标题"), "史記·高祖本紀");
    await user.type(screen.getByLabelText("初始文本"), "高祖，沛豐邑中陽里人。");
    await user.click(screen.getByRole("button", { name: "保存材料" }));

    expect(await screen.findByTestId("source-feedback")).toHaveTextContent("同题材料已存在");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("shows a readable failure when saving cannot reach the service", async () => {
    server.use(http.post("/v1/sources", () => HttpResponse.error()));
    const user = userEvent.setup();
    render(<SourceForm onSaved={() => undefined} />);

    await user.type(screen.getByLabelText("标题"), "漢書·藝文志");
    await user.type(screen.getByLabelText("初始文本"), "漢興，改秦之敗。");
    await user.click(screen.getByRole("button", { name: "保存材料" }));

    expect(await screen.findByTestId("source-feedback")).toHaveTextContent("无法连接服务");
  });

  it("imports a UTF-8 .txt file into the initial text area", async () => {
    const user = userEvent.setup();
    render(<SourceForm onSaved={() => undefined} />);
    const file = new File(["帝曰：善。"], "quote.txt", { type: "text/plain" });

    await user.upload(screen.getByLabelText("导入 .txt 文件（UTF-8）"), file);

    await waitFor(() => expect(screen.getByLabelText("初始文本")).toHaveValue("帝曰：善。"));
  });
});

describe("source list", () => {
  it("shows the empty state when there are no materials", async () => {
    render(<SourceListView onOpen={() => undefined} />);

    expect(await screen.findByTestId("sources-empty")).toHaveTextContent("暂无材料");
  });

  it("lists materials with version counts and opens one on click", async () => {
    server.use(sourcesListHandler);
    const onOpen = vi.fn();
    const user = userEvent.setup();
    render(<SourceListView onOpen={onOpen} />);

    const item = await screen.findByText("史記·秦始皇本紀");
    expect(screen.getByText(/版本 2/)).toBeVisible();
    await user.click(item);

    expect(onOpen).toHaveBeenCalledWith("11111111-1111-4111-8111-111111111111");
  });

  it("searches with the q parameter and reports an empty result", async () => {
    server.use(sourcesListHandler);
    const user = userEvent.setup();
    render(<SourceListView onOpen={() => undefined} />);
    await screen.findByText("史記·秦始皇本紀");

    await user.type(screen.getByLabelText("搜索材料"), "漢書");

    await waitFor(() => expect(screen.getByTestId("sources-empty")).toBeVisible());
  });

  it("shows the failure state when the service is unreachable", async () => {
    server.use(networkFailureSourcesHandler);
    render(<SourceListView onOpen={() => undefined} />);

    expect(await screen.findByTestId("load-error")).toHaveTextContent("无法连接服务");
  });

  it("reveals the add-material form and hides it again", async () => {
    const user = userEvent.setup();
    render(<SourceListView onOpen={() => undefined} />);

    await user.click(screen.getByRole("button", { name: "添加材料" }));
    expect(screen.getByRole("button", { name: "保存材料" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "取消添加" }));
    expect(screen.queryByRole("button", { name: "保存材料" })).toBeNull();
  });
});
