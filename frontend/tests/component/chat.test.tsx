import { render, screen, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ChatView } from "../../src/components/chat/ChatView";
import { server } from "../mocks/server";

const CONVERSATION = {
  id: "3cf22914-9798-49f6-bb28-1bc602077153",
  title: "于謙在守禦中的作用?",
  created_at: "2026-10-18T15:01:34.082174+08:00",
  updated_at: "2026-10-18T15:02:00.000000+08:00",
};

const ANSWER = "## 结论\n\n于謙主張固守京師。";

const SSE_BODY = [
  'event: message_start\ndata: {"message_id":"a1"}\n\n',
  'event: tool_call\ndata: {"tool":"search","arguments":{"query":"于謙"}}\n\n',
  'event: tool_result\ndata: {"tool":"search","result":{"ok":true,"hits":[{"version_id":"v-1","start":0,"end":2,"quote":"于謙","work":"明史","volume":"卷170"}]}}\n\n',
  `event: token\ndata: ${JSON.stringify({ text: ANSWER })}\n\n`,
  `event: citation_check\ndata: ${JSON.stringify({
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
  })}\n\n`,
  'event: review\ndata: {"verdict":"pass","error":null,"comments":[]}\n\n',
  `event: message_end\ndata: ${JSON.stringify({
    answer: ANSWER,
    usage: { input: 10, output: 20 },
    claims: 1,
    verified: 1,
  })}\n\n`,
].join("");

function handlers(): void {
  let sent = false;
  server.use(
    http.get("/v1/conversations", () => HttpResponse.json([CONVERSATION])),
    http.post("/v1/conversations", () =>
      HttpResponse.json(
        { ...CONVERSATION, id: "11111111-1111-4111-8111-111111111111" },
        { status: 201 },
      ),
    ),
    http.get("/v1/conversations/:id", () =>
      HttpResponse.json({
        conversation: CONVERSATION,
        messages: [
          {
            id: "99999999-9999-4999-8999-999999999999",
            role: "user",
            content: "京師指哪里?",
            status: "done",
            error: null,
            created_at: "2026-10-18T15:01:40.000000+08:00",
            events: [],
          },
          ...(sent
            ? [
                {
                  id: "88888888-8888-4888-8888-888888888888",
                  role: "assistant",
                  content: ANSWER,
                  status: "done",
                  error: null,
                  created_at: "2026-10-18T15:01:41.000000+08:00",
                  events: storedAssistantEvents,
                },
              ]
            : []),
        ],
      }),
    ),
    http.post("/v1/conversations/:id/messages", () => {
      sent = true;
      return new HttpResponse(SSE_BODY, { headers: { "Content-Type": "text/event-stream" } });
    }),
    http.post("/v1/messages/:id/stop", () =>
      HttpResponse.json({ message_id: "a1", stopped: true }),
    ),
  );
}

const storedAssistantEvents = [
  { seq: 1, kind: "tool_call", payload: { tool: "search", arguments: { query: "于謙" } } },
  {
    seq: 2,
    kind: "tool_result",
    payload: {
      tool: "search",
      result: { ok: true, hits: [{ version_id: "v-1", start: 0, end: 2, quote: "于謙" }] },
    },
  },
  { seq: 3, kind: "token", payload: { text: ANSWER } },
  {
    seq: 4,
    kind: "citation_check",
    payload: {
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
    },
  },
  { seq: 5, kind: "review", payload: { verdict: "pass", error: null, comments: [] } },
  {
    seq: 6,
    kind: "message_end",
    payload: { usage: { input: 10, output: 20 }, claims: 1, verified: 1 },
  },
];

describe("chat view", () => {
  it("lists conversations and shows stored messages", async () => {
    handlers();
    render(<ChatView />);

    expect(await screen.findByText("于謙在守禦中的作用?")).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", { name: /于謙在守禦中的作用/ }));

    expect(await screen.findByText("京師指哪里?")).toBeInTheDocument();
  });

  it("shows the greeting until a conversation has messages", async () => {
    handlers();
    render(<ChatView />);

    expect(await screen.findByText("你好，让我们开始聊天吧")).toBeInTheDocument();
  });

  it("streams an answer, renders tools, citations and the review verdict", async () => {
    handlers();
    render(<ChatView />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: /于謙在守禦中的作用/ }));

    const composer = await screen.findByLabelText("输入消息");
    await user.type(composer, "京師指哪里?{Enter}");

    expect(await screen.findByRole("heading", { name: "结论" })).toBeInTheDocument();
    expect(screen.getByText(/search · 命中 1 处/)).toBeInTheDocument();
    expect(screen.getByText("于謙請駐兵居庸，寇來則出關勦殺，退則就糧京師。")).toBeInTheDocument();
    expect(screen.getByText(/明通鑑·卷029/)).toBeInTheDocument();
    expect(document.body.textContent).not.toContain("3587");
    expect(screen.getByText("评审：pass")).toBeInTheDocument();
  });

  it("creates a conversation, lists it and selects it", async () => {
    const createdConversation = {
      ...CONVERSATION,
      id: "11111111-1111-4111-8111-111111111111",
      title: "新建的会话",
    };
    let created = false;
    server.use(
      http.get("/v1/conversations", () =>
        HttpResponse.json(created ? [createdConversation, CONVERSATION] : [CONVERSATION]),
      ),
      http.post("/v1/conversations", () => {
        created = true;
        return HttpResponse.json(createdConversation, { status: 201 });
      }),
      http.get("/v1/conversations/:id", () =>
        HttpResponse.json({ conversation: createdConversation, messages: [] }),
      ),
    );
    render(<ChatView />);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "开启新对话" }));

    expect(await screen.findByText("新建的会话")).toBeInTheDocument();
    await waitFor(() =>
      expect(document.querySelectorAll('.chat-groups button[aria-current="true"]')).toHaveLength(1),
    );
  });

  it("reports a failed stream and offers a retry", async () => {
    handlers();
    server.use(http.post("/v1/conversations/:id/messages", () => HttpResponse.error()));
    render(<ChatView />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: /于謙在守禦中的作用/ }));

    await user.type(await screen.findByLabelText("输入消息"), "京師指哪里?{Enter}");

    expect(await screen.findByRole("alert")).toHaveTextContent("本轮生成失败");
    expect(screen.getByRole("button", { name: "重试" })).toBeInTheDocument();
  });
});

describe("chat failure handling", () => {
  it("reports a non-2xx stream and retries the same message", async () => {
    let attempts = 0;
    server.use(
      http.get("/v1/conversations", () => HttpResponse.json([CONVERSATION])),
      http.get("/v1/conversations/:id", () =>
        HttpResponse.json({ conversation: CONVERSATION, messages: [] }),
      ),
      http.post("/v1/conversations/:id/messages", () => {
        attempts += 1;
        return attempts === 1
          ? HttpResponse.json({ detail: { code: "busy" } }, { status: 500 })
          : new HttpResponse(SSE_BODY, { headers: { "Content-Type": "text/event-stream" } });
      }),
    );
    render(<ChatView />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: /于謙在守禦中的作用/ }));

    await user.type(await screen.findByLabelText("输入消息"), "京師指哪里?{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent("本轮生成失败");

    await user.click(screen.getByRole("button", { name: "重试" }));
    await waitFor(() => expect(attempts).toBe(2));
  });

  it("does not send an empty draft", async () => {
    let attempts = 0;
    server.use(
      http.get("/v1/conversations", () => HttpResponse.json([CONVERSATION])),
      http.get("/v1/conversations/:id", () =>
        HttpResponse.json({ conversation: CONVERSATION, messages: [] }),
      ),
      http.post("/v1/conversations/:id/messages", () => {
        attempts += 1;
        return new HttpResponse(SSE_BODY, { headers: { "Content-Type": "text/event-stream" } });
      }),
    );
    render(<ChatView />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: /于謙在守禦中的作用/ }));

    await user.type(await screen.findByLabelText("输入消息"), "{Enter}");

    await waitFor(() => expect(attempts).toBe(0));
  });
});

describe("chat streaming controls", () => {
  it("offers stop while streaming and asks the server to finish the turn", async () => {
    const stopCalls: string[] = [];
    const encoder = new TextEncoder();
    server.use(
      http.get("/v1/conversations", () => HttpResponse.json([CONVERSATION])),
      http.get("/v1/conversations/:id", () =>
        HttpResponse.json({ conversation: CONVERSATION, messages: [] }),
      ),
      http.post("/v1/conversations/:id/messages", () => {
        const stream = new ReadableStream({
          start(controller) {
            controller.enqueue(
              encoder.encode(
                'event: message_start\ndata: {"message_id":"88888888-8888-4888-8888-888888888888"}\n\n',
              ),
            );
            controller.enqueue(encoder.encode('event: token\ndata: {"text":"部分"}\n\n'));
          },
        });
        return new HttpResponse(stream, {
          headers: { "Content-Type": "text/event-stream" },
        });
      }),
      http.post("/v1/messages/:id/stop", ({ params }) => {
        stopCalls.push(String(params.id));
        return HttpResponse.json({ message_id: params.id, stopped: true });
      }),
    );
    render(<ChatView />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: /于謙在守禦中的作用/ }));
    await user.type(await screen.findByLabelText("输入消息"), "京師指哪里?{Enter}");

    const stop = await screen.findByRole("button", { name: "中止" });
    await user.click(stop);

    await waitFor(() => expect(stopCalls).toContain("88888888-8888-4888-8888-888888888888"));
    expect(await screen.findByRole("alert")).toHaveTextContent("已中止本轮生成。");
  });
});

describe("conversation sidebar", () => {
  it("collapses and expands the conversation list", async () => {
    handlers();
    render(<ChatView />);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "收起会话" }));
    expect(screen.queryByRole("button", { name: "开启新对话" })).toBeNull();
    expect(screen.getByRole("button", { name: "展开会话" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "展开会话" }));
    expect(await screen.findByRole("button", { name: "开启新对话" })).toBeInTheDocument();
  });
});
