import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CitationList } from "../../src/components/chat/CitationChip";
import { MessageBubble } from "../../src/components/chat/MessageBubble";
import { ToolCallCard } from "../../src/components/chat/ToolCallCard";

const CITATION_PAYLOAD = {
  statement: "于謙主張固守京師。",
  ok: true,
  citations: [
    {
      version_id: "0013e595-4bc1-4c49-81e7-251e1ea8cb3d",
      start: 3587,
      end: 3610,
      exact_quote: "于謙請駐兵居庸，寇來則出關勦殺，退則就糧京師。",
      ok: true,
      code: null,
      work: "明通鑑",
      volume: "卷029",
    },
  ],
};

describe("tool call card", () => {
  it("renders nothing without tool events", () => {
    const { container } = render(<ToolCallCard events={[{ kind: "token", payload: {} }]} />);

    expect(container).toBeEmptyDOMElement();
  });

  it("summarises hits, reads, papers and failures", () => {
    const { rerender } = render(
      <ToolCallCard
        events={[
          { kind: "tool_call", payload: { tool: "search", arguments: { query: "于謙" } } },
          {
            kind: "tool_result",
            payload: {
              tool: "search",
              result: { ok: true, hits: [{ version_id: "v" }, { version_id: "w" }] },
            },
          },
        ]}
      />,
    );
    expect(screen.getByText(/search · 命中 2 处/)).toBeInTheDocument();

    rerender(
      <ToolCallCard
        events={[
          { kind: "tool_call", payload: { tool: "read", arguments: {} } },
          {
            kind: "tool_result",
            payload: { tool: "read", result: { ok: true, text: "京師戒嚴" } },
          },
        ]}
      />,
    );
    expect(screen.getByText(/read · 读取 4 字/)).toBeInTheDocument();

    rerender(
      <ToolCallCard
        events={[
          { kind: "tool_call", payload: { tool: "search_papers", arguments: {} } },
          {
            kind: "tool_result",
            payload: {
              tool: "search_papers",
              result: { ok: true, records: [{ title: "a" }], errors: ["crossref:500"] },
            },
          },
        ]}
      />,
    );
    expect(screen.getByText(/题录 1 条，1 个来源失败/)).toBeInTheDocument();

    rerender(
      <ToolCallCard
        events={[
          { kind: "tool_call", payload: { tool: "search", arguments: {} } },
          {
            kind: "tool_result",
            payload: { tool: "search", result: { ok: false, code: "empty_query" } },
          },
        ]}
      />,
    );
    expect(screen.getByText(/search · 未成功：empty_query/)).toBeInTheDocument();
  });

  it("reports a completed call with no recognised payload", () => {
    render(
      <ToolCallCard
        events={[
          { kind: "tool_call", payload: { tool: "unknown", arguments: {} } },
          { kind: "tool_result", payload: { tool: "unknown", result: {} } },
        ]}
      />,
    );

    expect(screen.getByText(/unknown · 已完成/)).toBeInTheDocument();
  });

  it("shows a pending state until the result arrives", () => {
    render(
      <ToolCallCard events={[{ kind: "tool_call", payload: { tool: "search", arguments: {} } }]} />,
    );

    expect(screen.getByText(/search · 执行中…/)).toBeInTheDocument();
  });
});

describe("citation list", () => {
  it("marks a failed check and shows the source range", () => {
    const payload = {
      ...CITATION_PAYLOAD,
      ok: false,
      citations: [{ ...CITATION_PAYLOAD.citations[0], ok: false, code: "quote_mismatch" }],
    };
    render(<CitationList citations={[payload]} />);

    expect(screen.getByText(/明通鑑·卷029 3587-3610/)).toBeInTheDocument();
    expect(screen.getByText(/quote_mismatch/)).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("falls back to the version id when labels are missing and ignores bad payloads", () => {
    render(
      <CitationList
        citations={[
          { citations: "nope" },
          {
            citations: [
              {
                version_id: "0013e595-4bc1-4c49-81e7-251e1ea8cb3d",
                start: 1,
                end: 3,
                exact_quote: "京師",
                ok: true,
                code: null,
              },
              "not-an-object",
              { start: 1, end: 3 },
              { version_id: 7, exact_quote: "数字版本" },
            ],
          },
        ]}
      />,
    );

    expect(screen.getByText(/0013e595 1-3/)).toBeInTheDocument();
  });

  it("renders nothing when there are no citations", () => {
    const { container } = render(<CitationList citations={[]} />);

    expect(container).toBeEmptyDOMElement();
  });
});

describe("message bubble", () => {
  it("renders user text plainly", () => {
    render(
      <MessageBubble author="user" content="京師指哪里?" events={[]} status="done" error={null} />,
    );

    expect(screen.getByText("京師指哪里?")).toBeInTheDocument();
  });

  it("renders an assistant answer with review verdict and failure state", () => {
    render(
      <MessageBubble
        author="assistant"
        content="## 结论"
        events={[
          { kind: "review", payload: { verdict: "fail", comments: [] } },
          { kind: "citation_check", payload: CITATION_PAYLOAD },
        ]}
        status="failed"
        error="timeout"
      />,
    );

    expect(screen.getByRole("heading", { name: "结论" })).toBeInTheDocument();
    expect(screen.getByText("评审：fail")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("本轮未完成：timeout");
  });

  it("marks a stopped turn", () => {
    render(
      <MessageBubble
        author="assistant"
        content="部分回答"
        events={[]}
        status="stopped"
        error={null}
      />,
    );

    expect(screen.getByText("已按请求中止。")).toBeInTheDocument();
  });
});
