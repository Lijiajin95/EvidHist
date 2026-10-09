import { render, screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ClaimDetailView } from "../../src/components/claims/ClaimDetailView";
import type { PendingQuote } from "../../src/domain/pendingQuote";
import { CLAIM_ID, VERSION_ID } from "../mocks/workbenchFixtures";
import {
  bindEvidenceExistingHandler,
  bindEvidenceHandler,
  bindEvidenceInvalidRangeHandler,
  bindVersionNotFoundHandler,
  claimDetailHandler,
  claimNotFoundHandler,
  networkFailureBindHandler,
  sourceDetailHandler,
  sourcesListHandler,
} from "../mocks/workbenchHandlers";
import { server } from "../mocks/server";

const pendingQuote: PendingQuote = {
  versionId: VERSION_ID,
  versionLabel: "整理稿一",
  start: 4,
  end: 5,
  quote: "𠀀",
};

function renderManualDetail() {
  const onBound = vi.fn();
  render(
    <ClaimDetailView
      claimId={CLAIM_ID}
      pendingQuote={null}
      onQuoteConsumed={() => undefined}
      onBack={() => undefined}
      onBound={onBound}
    />,
  );
  return { onBound };
}

function renderDetail(quote: PendingQuote | null = null) {
  const onQuoteConsumed = vi.fn();
  const onBound = vi.fn();
  render(
    <ClaimDetailView
      claimId={CLAIM_ID}
      pendingQuote={quote}
      onQuoteConsumed={onQuoteConsumed}
      onBack={() => undefined}
      onBound={onBound}
    />,
  );
  return { onQuoteConsumed, onBound };
}

describe("claim detail", () => {
  it("shows the claim as unverified and its evidence entries per source", async () => {
    server.use(claimDetailHandler());
    renderDetail();

    expect(await screen.findByText("秦並天下在三十六年。")).toBeVisible();
    expect(screen.getByText(/未核查/)).toBeVisible();
    const entry = screen.getByTestId("evidence-list");
    expect(entry).toHaveTextContent("史記·秦始皇本紀");
    expect(entry).toHaveTextContent("整理稿一");
    expect(entry).toHaveTextContent("秦並");
    expect(entry).toHaveTextContent("支持");
    expect(screen.getByText(/不代表史实已经证实/)).toBeVisible();
  });

  it("shows a readable error when the claim is gone", async () => {
    server.use(claimNotFoundHandler);
    renderDetail();

    expect(await screen.findByText("论断不存在或已被删除。")).toBeVisible();
  });

  it("binds a prefilled selection as evidence and consumes the pending quote", async () => {
    server.use(claimDetailHandler(), bindEvidenceHandler);
    const { onQuoteConsumed, onBound } = renderDetail(pendingQuote);
    const user = userEvent.setup();

    await screen.findByText("秦並天下在三十六年。");
    await user.click(screen.getByRole("button", { name: "新增证据绑定" }));
    expect(screen.getByTestId("prefilled-quote")).toHaveTextContent("区间 [4, 5)");
    await user.selectOptions(screen.getByLabelText("关系"), "supports");
    await user.click(screen.getByRole("button", { name: "绑定证据" }));

    expect(await screen.findByTestId("evidence-feedback")).toHaveTextContent("已绑定证据");
    expect(onQuoteConsumed).toHaveBeenCalled();
    expect(onBound).toHaveBeenCalled();
  });

  it("shows a readable error for an invalid range from the server", async () => {
    server.use(claimDetailHandler(), bindEvidenceInvalidRangeHandler);
    renderDetail(pendingQuote);
    const user = userEvent.setup();

    await screen.findByText("秦並天下在三十六年。");
    await user.click(screen.getByRole("button", { name: "新增证据绑定" }));
    await user.selectOptions(screen.getByLabelText("关系"), "contradicts");
    await user.click(screen.getByRole("button", { name: "绑定证据" }));

    expect(await screen.findByTestId("evidence-feedback")).toHaveTextContent("区间无效");
  });

  it("binds evidence picked manually from a source and version", async () => {
    server.use(
      claimDetailHandler(),
      sourcesListHandler,
      sourceDetailHandler(),
      bindEvidenceHandler,
    );
    const { onBound } = renderManualDetail();
    const user = userEvent.setup();

    await screen.findByText("秦並天下在三十六年。");
    await user.click(screen.getByRole("button", { name: "新增证据绑定" }));
    await user.selectOptions(
      screen.getByLabelText("选择材料"),
      "11111111-1111-4111-8111-111111111111",
    );
    await user.selectOptions(
      screen.getByLabelText("选择版本"),
      "22222222-2222-4222-8222-222222222222",
    );
    await user.type(screen.getByLabelText("起点（Unicode 码点，含）"), "0");
    await user.type(screen.getByLabelText("终点（Unicode 码点，不含）"), "2");
    await user.type(screen.getByLabelText("引文"), "秦並");
    await user.selectOptions(screen.getByLabelText("关系"), "supports");
    await user.click(screen.getByRole("button", { name: "绑定证据" }));

    expect(await screen.findByTestId("evidence-feedback")).toHaveTextContent("已绑定证据");
    expect(onBound).toHaveBeenCalled();
  });

  it("blocks a manual binding with missing fields", async () => {
    server.use(claimDetailHandler(), sourcesListHandler, sourceDetailHandler());
    const user = userEvent.setup();
    renderManualDetail();

    await screen.findByText("秦並天下在三十六年。");
    await user.click(screen.getByRole("button", { name: "新增证据绑定" }));
    await user.click(screen.getByRole("button", { name: "绑定证据" }));

    expect(await screen.findByTestId("evidence-feedback")).toHaveTextContent("请选择版本、关系");
  });

  it("reports a contract-violating response as an invalid response", async () => {
    server.use(
      claimDetailHandler(),
      http.post("/v1/claims/:id/evidence", () => HttpResponse.json({ unexpected: true })),
    );
    renderDetail(pendingQuote);
    const user = userEvent.setup();

    await screen.findByText("秦並天下在三十六年。");
    await user.click(screen.getByRole("button", { name: "新增证据绑定" }));
    await user.selectOptions(screen.getByLabelText("关系"), "supports");
    await user.click(screen.getByRole("button", { name: "绑定证据" }));

    expect(await screen.findByTestId("evidence-feedback")).toHaveTextContent("非法响应");
  });

  it("reports an idempotent retry as the existing evidence binding", async () => {
    server.use(claimDetailHandler(), bindEvidenceExistingHandler);
    renderDetail(pendingQuote);
    const user = userEvent.setup();

    await screen.findByText("秦並天下在三十六年。");
    await user.click(screen.getByRole("button", { name: "新增证据绑定" }));
    await user.selectOptions(screen.getByLabelText("关系"), "supports");
    await user.click(screen.getByRole("button", { name: "绑定证据" }));

    expect(await screen.findByTestId("evidence-feedback")).toHaveTextContent("相同证据已存在");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("shows the empty evidence state", async () => {
    server.use(claimDetailHandler([]));
    renderDetail();

    expect(await screen.findByTestId("evidence-empty")).toHaveTextContent("还没有绑定证据");
  });

  it("shows a network failure message when binding cannot reach the service", async () => {
    server.use(claimDetailHandler(), networkFailureBindHandler);
    renderDetail(pendingQuote);
    const user = userEvent.setup();

    await screen.findByText("秦並天下在三十六年。");
    await user.click(screen.getByRole("button", { name: "新增证据绑定" }));
    await user.selectOptions(screen.getByLabelText("关系"), "supports");
    await user.click(screen.getByRole("button", { name: "绑定证据" }));

    expect(await screen.findByTestId("evidence-feedback")).toHaveTextContent("无法连接服务");
  });

  it("shows a readable error when the bound version does not exist", async () => {
    server.use(claimDetailHandler(), bindVersionNotFoundHandler);
    renderDetail(pendingQuote);
    const user = userEvent.setup();

    await screen.findByText("秦並天下在三十六年。");
    await user.click(screen.getByRole("button", { name: "新增证据绑定" }));
    await user.selectOptions(screen.getByLabelText("关系"), "mentions");
    await user.click(screen.getByRole("button", { name: "绑定证据" }));

    expect(await screen.findByTestId("evidence-feedback")).toHaveTextContent("文本版本不存在");
  });
});
