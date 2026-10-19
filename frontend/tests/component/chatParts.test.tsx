import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CitationList } from "../../src/components/chat/CitationChip";
import { MessageBubble } from "../../src/components/chat/MessageBubble";
import { ToolCallCard } from "../../src/components/chat/ToolCallCard";
import type { StreamEvent } from "../../src/domain/chatContract";

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

  it("lists search hits as material, volume and text", () => {
    const { container } = render(
      <ToolCallCard
        events={[
          { kind: "tool_call", payload: { tool: "search", arguments: { query: "于謙" } } },
          {
            kind: "tool_result",
            payload: {
              tool: "search",
              result: {
                ok: true,
                hits: [
                  {
                    version_id: "0013e595-4bc1-4c49-81e7-251e1ea8cb3d",
                    start: 3607,
                    end: 3609,
                    quote: "京師",
                    context: "退則就糧京師。大同參將許貴奏",
                    work: "明通鑑",
                    volume: "卷029",
                  },
                ],
              },
            },
          },
        ]}
      />,
    );

    expect(screen.getByText("search · 命中 1 处")).toBeInTheDocument();
    expect(screen.getByText("检索词：于謙")).toBeInTheDocument();
    expect(screen.getByText("明通鑑·卷029")).toBeInTheDocument();
    expect(screen.getByText("京師")).toBeInTheDocument();
    expect(container.textContent).not.toContain("0013e595");
    expect(container.textContent).not.toContain("3607");
  });

  it("never shows a version id in arguments even when the model passes one", () => {
    const { container } = render(
      <ToolCallCard
        events={[
          {
            kind: "tool_call",
            payload: {
              tool: "verify_citation",
              arguments: {
                version_id: "0013e595-4bc1-4c49-81e7-251e1ea8cb3d",
                start: 3587,
                end: 3610,
                exact_quote: "于謙請駐兵居庸，寇來則出關勦殺，退則就糧京師。",
              },
            },
          },
          {
            kind: "tool_result",
            payload: {
              tool: "verify_citation",
              result: {
                ok: true,
                code: null,
                exact_quote: "于謙請駐兵居庸，寇來則出關勦殺，退則就糧京師。",
              },
            },
          },
        ]}
      />,
    );

    expect(
      screen.getByText("原文：于謙請駐兵居庸，寇來則出關勦殺，退則就糧京師。"),
    ).toBeInTheDocument();
    expect(screen.getByText("通过程序校验")).toBeInTheDocument();
    expect(container.textContent).not.toContain("0013e595");
    expect(container.textContent).not.toContain("3587");
  });

  it("summarises materials, reads, papers and failures readably", () => {
    const { rerender } = render(
      <ToolCallCard
        events={[
          { kind: "tool_call", payload: { tool: "list_materials", arguments: {} } },
          {
            kind: "tool_result",
            payload: {
              tool: "list_materials",
              result: {
                ok: true,
                materials: [
                  {
                    version_id: "0013e595-4bc1-4c49-81e7-251e1ea8cb3d",
                    work: "明通鑑",
                    volume: "卷029",
                    chars: 17136,
                  },
                ],
              },
            },
          },
        ]}
      />,
    );
    expect(screen.getByText("明通鑑·卷029")).toBeInTheDocument();
    expect(screen.getByText("17136 字")).toBeInTheDocument();

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
    expect(screen.getByText("read · 读取 4 字")).toBeInTheDocument();
    expect(screen.getByText("京師戒嚴")).toBeInTheDocument();

    rerender(
      <ToolCallCard
        events={[
          { kind: "tool_call", payload: { tool: "search_papers", arguments: {} } },
          {
            kind: "tool_result",
            payload: {
              tool: "search_papers",
              result: {
                ok: true,
                records: [{ title: "北京保卫战研究", year: 2019, venue: "明史研究" }],
                errors: ["crossref:500"],
              },
            },
          },
        ]}
      />,
    );
    expect(screen.getByText(/题录 1 条，1 个来源失败/)).toBeInTheDocument();
    expect(screen.getByText("北京保卫战研究")).toBeInTheDocument();

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
    expect(screen.getByText("search · 未成功：empty_query")).toBeInTheDocument();
  });

  it("labels later calls from earlier hits and stays quiet for unknown versions", () => {
    const hit = {
      version_id: "0013e595-4bc1-4c49-81e7-251e1ea8cb3d",
      start: 3607,
      end: 3609,
      quote: "京師",
      context: "退則就糧京師。",
      work: "明通鑑",
      volume: "卷029",
    };
    const { rerender, container } = render(
      <ToolCallCard
        events={[
          { kind: "tool_call", payload: { tool: "search", arguments: { query: "京師" } } },
          { kind: "tool_result", payload: { tool: "search", result: { ok: true, hits: [hit] } } },
          {
            kind: "tool_call",
            payload: {
              tool: "read",
              arguments: { version_id: hit.version_id, start: 3600, end: 3616 },
            },
          },
          {
            kind: "tool_result",
            payload: { tool: "read", result: { ok: true, text: "退則就糧京師。" } },
          },
        ]}
      />,
    );
    expect(screen.getAllByText("明通鑑·卷029").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/退則就糧京師。/).length).toBeGreaterThan(0);
    expect(container.textContent).not.toContain("0013e595");

    rerender(
      <ToolCallCard
        events={[
          {
            kind: "tool_call",
            payload: {
              tool: "read",
              arguments: { version_id: "ffffffff-ffff-4fff-8fff-ffffffffffff" },
            },
          },
        ]}
      />,
    );
    expect(screen.queryByText(/参数/)).toBeNull();
  });

  it("survives malformed events without leaking identifiers", () => {
    const { container } = render(
      <ToolCallCard
        events={[
          { kind: "tool_result", payload: "boom" } as unknown as StreamEvent,
          {
            kind: "tool_result",
            payload: {
              tool: "search",
              result: { ok: true, hits: [{ version_id: 7, quote: "京師" }] },
            },
          },
        ]}
      />,
    );

    expect(container.textContent).not.toContain("version_id");
    expect(container.textContent).not.toContain("7");
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

    expect(screen.getByText("unknown · 已完成")).toBeInTheDocument();
  });

  it("shows a pending state until the result arrives", () => {
    render(
      <ToolCallCard events={[{ kind: "tool_call", payload: { tool: "search", arguments: {} } }]} />,
    );

    expect(screen.getByText("search · 执行中…")).toBeInTheDocument();
  });
});

describe("citation list", () => {
  it("shows material, volume and the quote without internal identifiers", () => {
    const { container } = render(<CitationList citations={[CITATION_PAYLOAD]} />);

    expect(screen.getByText("于謙請駐兵居庸，寇來則出關勦殺，退則就糧京師。")).toBeInTheDocument();
    expect(screen.getByText(/明通鑑·卷029/)).toBeInTheDocument();
    expect(screen.getByText(/通过程序校验/)).toBeInTheDocument();
    expect(container.textContent).not.toContain("0013e595");
    expect(container.textContent).not.toContain("3587");
    expect(container.textContent).not.toContain("3610");
  });

  it("marks a failed check and never falls back to the version id", () => {
    const payload = {
      ...CITATION_PAYLOAD,
      ok: false,
      citations: [
        {
          ...CITATION_PAYLOAD.citations[0],
          ok: false,
          code: "quote_mismatch",
          work: undefined,
          volume: undefined,
        },
      ],
    };
    const { container } = render(<CitationList citations={[payload]} />);

    expect(screen.getByText(/出处未标注/)).toBeInTheDocument();
    expect(screen.getByText(/quote_mismatch/)).toBeInTheDocument();
    expect(container.textContent).not.toContain("0013e595");
  });

  it("falls back to a readable verdict when the failure carries no code", () => {
    render(
      <CitationList
        citations={[
          {
            citations: [
              {
                version_id: "0013e595-4bc1-4c49-81e7-251e1ea8cb3d",
                exact_quote: "京師",
                ok: false,
                code: null,
                work: "明通鑑",
                volume: "卷029",
              },
            ],
          },
        ]}
      />,
    );

    expect(screen.getByText(/未通过/)).toBeInTheDocument();
  });

  it("ignores malformed payloads and renders nothing when there are no citations", () => {
    const { container } = render(
      <CitationList
        citations={[
          { citations: "nope" },
          { citations: ["not-an-object", { start: 1, end: 3 }, { version_id: 7 }] },
        ]}
      />,
    );

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

describe("tool result view", () => {
  function events(tool: string, result: unknown): StreamEvent[] {
    return [
      { kind: "tool_call", payload: { tool, arguments: {} } },
      {
        kind: "tool_result",
        payload: { tool, result: result },
      },
    ];
  }

  it("renders quotes, paper metadata and reads without leaking identifiers", () => {
    const { rerender, container } = render(
      <ToolCallCard events={events("exact_quote", { ok: true, exact_quote: "京師" })} />,
    );
    expect(screen.getByText("京師")).toBeInTheDocument();

    rerender(
      <ToolCallCard
        events={events("search_papers", {
          ok: true,
          records: [{ title: "甲", year: 2019, venue: "明史研究" }, { title: "乙" }],
        })}
      />,
    );
    expect(screen.getByText("甲")).toBeInTheDocument();
    expect(screen.getByText(/2019 · 明史研究/)).toBeInTheDocument();
    expect(screen.getByText("乙")).toBeInTheDocument();

    rerender(
      <ToolCallCard
        events={events("list_materials", {
          ok: true,
          materials: [{ work: "明通鑑", volume: "卷029", chars: 17136 }, { work: "明史" }],
        })}
      />,
    );
    expect(screen.getByText("明史")).toBeInTheDocument();

    rerender(<ToolCallCard events={events("read", { ok: true })} />);
    expect(container.textContent).not.toContain("version_id");
  });

  it("shows nothing for failed or unknown tool results", () => {
    const { container, rerender } = render(
      <ToolCallCard events={events("search", { ok: false, code: "empty_query" })} />,
    );
    expect(container.querySelector(".chat-tool-list")).toBeNull();

    rerender(<ToolCallCard events={events("mystery", { ok: true, weird: 1 })} />);
    expect(screen.getByText("mystery · 已完成")).toBeInTheDocument();
    expect(container.querySelector(".chat-tool-list")).toBeNull();
  });

  it("tolerates events without usable tool metadata", () => {
    const { container, rerender } = render(
      <ToolCallCard events={[{ kind: "tool_call", payload: { arguments: "not-an-object" } }]} />,
    );
    expect(screen.getByText(/tool · 执行中…/)).toBeInTheDocument();

    rerender(
      <ToolCallCard
        events={[
          { kind: "tool_call", payload: { tool: "search", arguments: null } },
          {
            kind: "tool_result",
            payload: {
              tool: "search",
              result: { ok: true, hits: [{ version_id: 7, quote: "京師" }, "not-an-object"] },
            },
          },
        ]}
      />,
    );
    expect(screen.getByText("京師")).toBeInTheDocument();
    expect(screen.getAllByText("出处未标注").length).toBeGreaterThan(0);
    expect(container.textContent).not.toContain("version_id");
  });
});
