import { render, screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "../../src/App";
import { ToolView } from "../../src/components/ToolView";
import {
  delayedSuccessHandler,
  emptyResultHandler,
  invalidResponseHandler,
  networkFailureHandler,
  nonJsonErrorHandler,
  unknownCodeHandler,
  versionMismatchHandler,
} from "../mocks/handlers";
import { server } from "../mocks/server";

interface FormInput {
  textVersion?: string;
  citationVersion?: string;
  text?: string;
  start?: string;
  end?: string;
  quote?: string;
}

async function fillAndSubmit(user: ReturnType<typeof userEvent.setup>, input: FormInput) {
  await user.type(screen.getByLabelText("文本版本编号"), input.textVersion ?? "v1");
  await user.type(screen.getByLabelText("引文版本编号"), input.citationVersion ?? "v1");
  await user.type(screen.getByLabelText("文本（本界面只校验此文本）"), input.text ?? "甲𠀀乙");
  await user.type(screen.getByLabelText("起点（Unicode 码点，含）"), input.start ?? "1");
  await user.type(screen.getByLabelText("终点（Unicode 码点，不含）"), input.end ?? "2");
  await user.type(screen.getByLabelText("引文"), input.quote ?? "𠀀");
  await user.click(screen.getByRole("button", { name: "校验位置" }));
}

describe("app shell", () => {
  it("exposes the chat as the only interaction surface", async () => {
    server.use(http.get("/v1/conversations", () => HttpResponse.json([])));
    render(<App />);

    expect(await screen.findByText("你好，让我们开始聊天吧")).toBeInTheDocument();
    expect(screen.getByLabelText("输入消息")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "开启新对话" })).toBeInTheDocument();
    for (const hidden of ["材料", "论断", "引文定位工具"]) {
      expect(screen.queryByRole("button", { name: hidden })).toBeNull();
    }
  });
});

describe("quote locate tool（工作台视图，当前不作为界面入口）", () => {
  it("shows the located range and highlights the astral quote in the source text", async () => {
    const user = userEvent.setup();
    render(<ToolView />);

    await fillAndSubmit(user, { text: "甲𠀀乙", start: "1", end: "2", quote: "𠀀" });

    const result = await screen.findByTestId("locate-result");
    expect(result).toHaveTextContent("已定位：版本 v1，区间 [1, 2)。");
    expect(screen.getByTestId("highlighted-quote")).toHaveTextContent("𠀀");
    expect(screen.getByTestId("source-highlight")).toHaveTextContent("甲𠀀乙");
  });

  it("renders a readable error for a version mismatch instead of raw JSON", async () => {
    server.use(versionMismatchHandler);
    const user = userEvent.setup();
    render(<ToolView />);

    await fillAndSubmit(user, { citationVersion: "v2" });

    expect(await screen.findByTestId("locate-failure")).toHaveTextContent("版本不符");
  });

  it("shows the loading state while the check is in flight", async () => {
    server.use(delayedSuccessHandler(2000));
    const user = userEvent.setup();
    render(<ToolView />);

    await fillAndSubmit(user, {});

    expect(await screen.findByText("正在校验…")).toBeVisible();
  });

  it("reports a response that violates the contract as an invalid response", async () => {
    server.use(invalidResponseHandler);
    const user = userEvent.setup();
    render(<ToolView />);

    await fillAndSubmit(user, {});

    expect(await screen.findByTestId("locate-failure")).toHaveTextContent("非法响应");
  });

  it("reports an empty result instead of showing an empty success", async () => {
    server.use(emptyResultHandler);
    const user = userEvent.setup();
    render(<ToolView />);

    await fillAndSubmit(user, {});

    expect(await screen.findByTestId("locate-empty")).toHaveTextContent("结果为空");
  });

  it("reports a network failure when the service cannot be reached", async () => {
    server.use(networkFailureHandler);
    const user = userEvent.setup();
    render(<ToolView />);

    await fillAndSubmit(user, {});

    expect(await screen.findByTestId("locate-failure")).toHaveTextContent("网络失败");
  });

  it("treats an undocumented failure code as a contract violation", async () => {
    server.use(unknownCodeHandler);
    const user = userEvent.setup();
    render(<ToolView />);

    await fillAndSubmit(user, {});

    expect(await screen.findByTestId("locate-failure")).toHaveTextContent("非法响应");
  });

  it("reports a non-JSON error body as an invalid response", async () => {
    server.use(nonJsonErrorHandler);
    const user = userEvent.setup();
    render(<ToolView />);

    await fillAndSubmit(user, {});

    expect(await screen.findByTestId("locate-failure")).toHaveTextContent("非法响应");
  });

  it("blocks submission of an incomplete form with a readable alert", async () => {
    const user = userEvent.setup();
    render(<ToolView />);

    await user.click(screen.getByRole("button", { name: "校验位置" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("请完整填写");
    expect(screen.queryByText("正在校验…")).toBeNull();
  });

  it("canceling returns to idle and a late response cannot flip the state", async () => {
    server.use(delayedSuccessHandler(500));
    const user = userEvent.setup();
    render(<ToolView />);

    await fillAndSubmit(user, {});
    await user.click(await screen.findByRole("button", { name: "取消" }));

    expect(await screen.findByText("尚未提交校验请求。")).toBeVisible();
    await new Promise((resolve) => setTimeout(resolve, 700));
    expect(screen.queryByTestId("locate-result")).toBeNull();
    expect(screen.getByText("尚未提交校验请求。")).toBeVisible();
  });

  it("prevents a second submission while a request is in flight", async () => {
    server.use(delayedSuccessHandler(600));
    const user = userEvent.setup();
    render(<ToolView />);

    await fillAndSubmit(user, { start: "1", end: "2" });
    await screen.findByText("正在校验…");

    expect(screen.getByRole("button", { name: "校验位置" })).toBeDisabled();
    await new Promise((resolve) => setTimeout(resolve, 700));
    expect(await screen.findByTestId("locate-result")).toHaveTextContent("区间 [0, 1)。");
  });
});
