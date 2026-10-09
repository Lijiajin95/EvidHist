import { render, screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ClaimForm } from "../../src/components/claims/ClaimForm";
import { ClaimListView } from "../../src/components/claims/ClaimListView";
import {
  claimsListHandler,
  createClaimExistingHandler,
  createClaimHandler,
  networkFailureClaimsHandler,
} from "../mocks/workbenchHandlers";
import { server } from "../mocks/server";

describe("claim list", () => {
  it("shows the empty state when there are no claims", async () => {
    render(<ClaimListView onOpen={() => undefined} />);

    expect(await screen.findByTestId("claims-empty")).toHaveTextContent("暂无论断");
  });

  it("lists claims with review status and evidence counts, and opens one", async () => {
    server.use(claimsListHandler);
    const onOpen = vi.fn();
    const user = userEvent.setup();
    render(<ClaimListView onOpen={onOpen} />);

    const item = await screen.findByText("秦並天下在三十六年。");
    expect(screen.getByText(/未核查 · 证据 1/)).toBeVisible();
    await user.click(item);

    expect(onOpen).toHaveBeenCalledWith("33333333-3333-4333-8333-333333333333");
  });

  it("shows the failure state when the service is unreachable", async () => {
    server.use(networkFailureClaimsHandler);
    render(<ClaimListView onOpen={() => undefined} />);

    expect(await screen.findByTestId("load-error")).toHaveTextContent("无法连接服务");
  });
});

describe("claim form", () => {
  it("blocks an empty statement with a readable alert", async () => {
    const user = userEvent.setup();
    render(<ClaimForm onSaved={() => undefined} />);

    await user.click(screen.getByRole("button", { name: "保存论断" }));

    expect(await screen.findByTestId("claim-feedback")).toHaveTextContent("请填写 1–500 字");
  });

  it("creates a claim and reports it as unverified", async () => {
    server.use(createClaimHandler);
    const onSaved = vi.fn();
    const user = userEvent.setup();
    render(<ClaimForm onSaved={onSaved} />);

    await user.type(screen.getByLabelText("论断描述"), "項羽自立為西楚霸王。");
    await user.click(screen.getByRole("button", { name: "保存论断" }));

    expect(await screen.findByTestId("claim-feedback")).toHaveTextContent(
      "已创建论断（默认未核查）",
    );
    expect(onSaved).toHaveBeenCalled();
  });

  it("reports an idempotent retry as the existing claim", async () => {
    server.use(createClaimExistingHandler);
    const user = userEvent.setup();
    render(<ClaimForm onSaved={() => undefined} />);

    await user.type(screen.getByLabelText("论断描述"), "秦並天下在三十六年。");
    await user.click(screen.getByRole("button", { name: "保存论断" }));

    expect(await screen.findByTestId("claim-feedback")).toHaveTextContent("相同论断已存在");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("reveals the create-claim form from the list view", async () => {
    const user = userEvent.setup();
    render(<ClaimListView onOpen={() => undefined} />);

    await user.click(screen.getByRole("button", { name: "新建论断" }));
    expect(screen.getByRole("button", { name: "保存论断" })).toBeVisible();
    await user.click(screen.getByRole("button", { name: "取消新建" }));
    expect(screen.queryByRole("button", { name: "保存论断" })).toBeNull();
  });

  it("shows a readable failure when creating cannot reach the service", async () => {
    server.use(http.post("/v1/claims", () => HttpResponse.error()));
    const user = userEvent.setup();
    render(<ClaimForm onSaved={() => undefined} />);

    await user.type(screen.getByLabelText("论断描述"), "秦並天下在三十六年。");
    await user.click(screen.getByRole("button", { name: "保存论断" }));

    expect(await screen.findByTestId("claim-feedback")).toHaveTextContent("无法连接服务");
  });
});
