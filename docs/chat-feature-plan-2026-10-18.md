# 对话功能技术方案（2026-10-18）

面向[用户需求](../README.md)的新增能力：在工作台内提供**人机交互对话**，对话过程中可检索已入库史料、引用证据、校验引文、生成报告、请求评审，并可检索网络上的论文元数据。版式参考 DeepSeek 网页版（左侧会话列表、中间消息流、底部输入区）。

本方案按[研发纪律](development-discipline.md)提交评审。**2026-10-18 已确认开工**，决策见文末第 11 节。

## 1. 现状与复用（不重复造）

| 已有能力 | 位置 | 对话功能如何复用 |
| --- | --- | --- |
| 材料/不可变版本/引文定位 | `api_sources.py`、`domain/citations.py` | 作为只读检索与引文硬校验的底座 |
| 4 个只读资料工具 | `research/tools.py` | 直接作为对话工具集的第一部分 |
| PI 零工具 RPC + 宿主代理 | `research/pi_rpc.py`、`pi_executor.py` | 对话每一轮沿用同一接入方式，工具仍由宿主执行并记录 |
| 报告渲染与运行产物 | `research/report.py` | `draft_report` 工具复用渲染与落盘 |
| 单模型评审契约 | `research/review.py` | `request_review` 工具复用评审与失败记录 |
| 会话式前端骨架 | `App.tsx`、`Nav.tsx`、`api/*.ts` | 新增一个视图，不改动既有视图行为 |

## 2. 第一版用户可见行为

1. 侧栏：会话列表（标题、更新时间）、新建会话、切换会话；窄屏折叠。
2. 主区：消息流，用户/助手气泡区分；助手回复**逐字流式**出现；工具调用显示为可折叠卡片（检索资料、网络检索、引文校验、生成报告、评审），卡片内给出参数与结果摘要。
3. 引文：助手回答中的引文以可点击标记呈现，点击跳转到「材料与引用」视图并带出定位上下文（复用现有 `PendingQuote` 链路）。
4. 输入区：多行输入（Enter 发送、Shift+Enter 换行）、发送中可中止、失败可重试同一条消息。
5. 每次回答结束给出**本轮依据**：使用的工具、命中的版本与区间、引文校验结果、是否调用过评审。
6. 报告：对话中生成的报告写入 `runs/<run_id>/`（与现有产物同构），并在消息里给出路径与摘要。

## 3. 数据模型与迁移

新增 `migrations/0002_conversations.sql`：

| 表 | 字段（要点） | 说明 |
| --- | --- | --- |
| `conversations` | `id`、`title`、`created_at`、`updated_at` | 标题取首条用户消息前 40 字，可后续改名 |
| `messages` | `id`、`conversation_id`、`role`（user/assistant/system）、`content`、`status`（streaming/done/failed/stopped）、`error`、`created_at` | 助手消息在流式开始时插入，结束时更新状态 |
| `message_events` | `id`、`message_id`、`seq`、`kind`、`payload`（jsonb）、`created_at` | 工具调用、工具结果、引文校验、评审、运行产物等结构化事件；用于刷新后重建卡片 |

不变式：`messages.id` 幂等（客户端可用 `client_message_id` 去重，重复提交同一条不新建）；助手消息在 `status != done` 时不参与「历史上下文」组装；`message_events.seq` 在一条消息内单调递增。

## 4. API 契约

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/v1/conversations` | 新建会话，返回 `{id, title, created_at}` |
| GET | `/v1/conversations` | 列表（按 `updated_at` 倒序，分页） |
| GET | `/v1/conversations/{id}` | 会话详情 + 消息 + 事件（刷新恢复界面） |
| POST | `/v1/conversations/{id}/messages` | 提交用户消息并**流式**返回助手回复 |
| POST | `/v1/messages/{id}/stop` | 请求中止当前生成（幂等） |

流式采用 **SSE**（`text/event-stream`），事件类型：

```
message_start   {message_id}
token           {text}
tool_call       {seq, tool, arguments}
tool_result     {seq, tool, ok, summary, citations[]}
citation_check  {seq, version_id, start, end, exact_quote, ok, code}
review          {seq, verdict, comments[]}
run_artifact    {seq, run_id, files[]}
message_end     {message_id, status, usage{}, stopped_reason}
error           {code, message}
```

失败与中止都落到 `messages.status` 与最后一个事件，**不把未完成的回答当作正常结果**。

## 5. 执行器与工具

对话循环（`research/chat.py`）：宿主维护消息上下文 → 调 PI（零工具，`--no-session`）→ PI 以 JSON 输出「下一步动作」→ 宿主执行工具 → 结果回填 → 直到 PI 给出最终回答或达到上限。上限沿用 M07 口径：轮次、工具调用数、墙钟时间、空转超时，全部记入 `stopped_reason`。

工具集（v1，均为宿主执行）：

| 工具 | 行为 | 边界 |
| --- | --- | --- |
| `list_materials` / `search` / `read` / `exact_quote` | 复用现有 4 个只读工具 | 只读，不改材料 |
| `verify_citation` | 对**已入库版本**做程序硬校验（`locate_quote`） | 失败即失败，不做模糊匹配 |
| `draft_report` | 用本轮通过的论断与引文渲染报告并写入 `runs/<run_id>/` | 未通过校验的论断按现有规则标记 |
| `request_review` | 调 PiReviewer 评审当前报告草稿 | 缺评/超时记 `review_failed`，不视为通过 |
| `search_papers` | 检索外部论文**元数据**（标题、作者、年份、DOI、链接、来源库） | 见第 6 节；不下载全文 |
| `import_paper_record` | 把选定题录写入材料库（**已确认允许**），标注来源库、许可与检索时间 | 只入库题录字段；不抓全文；重复检索按 DOI/URL 幂等 |

## 6. 网络论文检索（已确认：OpenAlex + Crossref，允许入库题录）

- 来源：**OpenAlex 与 Crossref 双来源**，同一查询分别检索后合并去重（DOI 相同视为同一条，保留两处来源标记）。
- 入库（已确认）：题录可作为材料写入材料库，材料内容仅含题录字段（标题、作者、年份、发表处、DOI/链接、来源库、检索时间），`usage_terms` 必须写明来源库与许可（OpenAlex 元数据 CC0；Crossref 题录按其条款），`origin` 记录检索 URL 与时间；不抓取全文、不存摘要正文除非来源另有明确开放声明。
- 幂等：同一 DOI（或同一来源库的同一 URL）重复入库时命中既有来源，不新建材料。
- 证据边界不变：**引文证据仍必须来自已入库版本**；题录材料的正文即题录本身，不可被当作史料引文。

- 适配层 `research/papers.py`：单一 `PaperQuery` 接口 + 每个来源一个薄适配器；请求带超时、限速与 `User-Agent`，TLS 校验保持开启（受 SAST 规则约束）。
- 结果统一字段：`source`（来源库）、`title`、`authors`、`year`、`doi/url`、`retrieved_at`；界面与事件里必须显示来源库与检索时间。
- 缓存：同一查询在会话内复用，避免重复请求（写 `message_events`）。

**待你决定**：接入哪些来源（见文末问题）。

## 7. 前端设计（DeepSeek 网页版式）

布局：左侧 260px 会话栏（新建按钮 + 列表）、中间消息流（最大宽度 760px 居中）、底部输入区（圆角、发送/中止按钮）。气泡：用户右侧浅色、助手左侧无边框；工具卡片为浅灰描边、默认折叠。

新增文件：

| 文件 | 目的 |
| --- | --- |
| `frontend/src/components/chat/ChatView.tsx` | 三栏布局与数据装配（会话、消息、流式状态） |
| `frontend/src/components/chat/ConversationList.tsx` | 会话列表、新建、切换 |
| `frontend/src/components/chat/MessageBubble.tsx` | 消息气泡与 Markdown 渲染 |
| `frontend/src/components/chat/ToolCallCard.tsx` | 工具调用/结果折叠卡片 |
| `frontend/src/components/chat/CitationChip.tsx` | 可点击引文标记 → 跳转材料视图 |
| `frontend/src/api/chat.ts` | REST 调用 + `fetch` 流式解析（SSE） |
| `frontend/src/domain/chatContract.ts` | 消息与事件契约（zod 校验，未知事件安全忽略） |
| `frontend/src/styles.css`（修改） | 版式与响应式样式 |
| `frontend/src/components/Nav.tsx`（修改） | 增加「对话」入口 |
| `frontend/src/App.tsx`（修改） | 接入视图与引文跳转 |
| `frontend/tests/component/chat.test.tsx`、`frontend/tests/unit/chatStream.test.ts`、`frontend/tests/mocks/handlers.ts`（修改） | 组件的流式渲染、工具卡片、引文跳转、错误与中止路径 |

Markdown 渲染（已确认）：新增前端依赖 `react-markdown` + `remark-gfm`（默认转义 HTML，不渲染原始 HTML）。

## 8. 后端文件清单

| 文件 | 目的 |
| --- | --- |
| `migrations/0002_conversations.sql`（新增） | 3 张表与索引 |
| `src/evidhist/models.py`（修改） | `ConversationRow`、`MessageRow`、`MessageEventRow` |
| `src/evidhist/chat_service.py`（新增） | 会话/消息写入、状态流转、幂等与中止标记（先测试后实现） |
| `src/evidhist/api_conversations.py`（新增） | 第 4 节端点与 SSE 生成器 |
| `src/evidhist/api.py`（修改） | 注册路由 |
| `src/evidhist/research/chat.py`（新增） | 对话循环（上下文组装、工具中介、事件产出、上限） |
| `src/evidhist/research/chat_tools.py`（新增） | `verify_citation`、`draft_report`、`request_review`、`search_papers` |
| `src/evidhist/research/papers.py`（新增） | 外部论文元数据检索适配层 |
| `src/evidhist/research/pi_executor.py`（修改） | 抽出可复用的单轮调用入口（现为三固定阶段） |
| `tests/unit/test_chat_service.py`、`tests/unit/test_chat_tools.py`、`tests/unit/test_papers.py`、`tests/component/test_chat_stream.py`、`tests/integration/test_conversation_store.py`（新增） | 状态流转与幂等、工具边界、流式事件顺序、真实 PG 下的会话读写 |
| `contracts/openapi.json`（修改） | API 契约快照 |
| `tests/integration/test_migrations.py`（修改） | 该测试固定了迁移清单，新增 `0002_conversations.sql` 后必须同步期望（含三张新表） |
| `docs/development.md`（修改） | 用法、限制与验证记录 |

## 9. 验证方式

- 后端：`make check`（含结构、类型、导入与依赖门槛）、`make coverage`（含 diff-cover 增量门槛）、`make test-integration`（真实 PG）、新增 SSE 组件测试校验事件顺序与错误/中止语义。
- 前端：`make frontend-check`（lint、类型、依赖、Knip、覆盖率）、`npm run e2e` 增加一条对话用例（新建会话 → 提问 → 工具卡片 → 引文跳转 → 中止/重试）。
- 真实试验：用 `deepseek-v4.1-flash` 跑一次真实对话（问题沿用「于謙在北京保衛戰中的作用」），核对工具调用、引文校验与评审记录，产物留在 `runs/`。
- 安全：`make security`（bandit 拦截 `verify=False` 等）；外部检索的来源、时限与不下载全文写入文档。

## 10. 第一版明确不做

- 多用户/共享会话、消息编辑与重新生成、附件与图片、语音、移动端专门适配；
- 把网络检索结果自动入库为材料或引文证据（引文证据只能来自已入库版本）；
- 全文抓取、绕过付费墙、批量下载；
- 对话内的多模型对比、自动选择模型。

## 11. 预算与未决事项

预算：约 18–24 小时（后端 10–12h、前端 6–8h、真实试验与文档 2–4h），分四步交付：①迁移与聊天服务（含测试）→ ②工具与外部检索 → ③SSE API → ④前端视图与 E2E。

### 已确认决策（2026-10-18）

| 项 | 决策 |
| --- | --- |
| 方案 | 按本方案开工，四步交付 |
| 论文检索来源 | **OpenAlex + Crossref 双来源**，DOI 去重合并 |
| 检索结果处置 | **允许写入材料库**（仅题录字段，标注来源库、许可与检索时间；DOI/URL 幂等；引文证据仍只能来自已入库版本） |
| 对话持久化 | **入库持久化**（3 张表 + 迁移） |
| Markdown 渲染 | **新增 `react-markdown` + `remark-gfm`**（默认转义 HTML） |

## 12. 实施进度（2026-10-18）

| 步骤 | 状态 | 证据 |
| --- | --- | --- |
| ① 迁移与聊天服务 | **已完成** | `migrations/0002_conversations.sql`、`models.py` 三表、`chat_service.py`；9 项集成测试通过（标题取值、客户端消息幂等、事件序号、未完成消息不进历史、结束幂等、级联删除）；演示库已应用迁移 |
| ② 对话工具与外部题录检索 | **已完成** | `research/papers.py`（OpenAlex + Crossref，DOI/标题去重、单源失败如实记录、不抓全文）+ 12 项单元测试；`research/chat_tools.py`（`verify_citation` 程序硬校验、`import_paper_record` 题录入库且重复导入幂等、题录正文/出处/许可文本、`request_review` 失败即失败）+ 8 项单元测试与 3 项集成测试；`httpx2` 由 dev 组移入运行时依赖 |
| ③ SSE API 与契约快照 | **已完成** | `pi_rpc.py` 新增 `stream_pi`（真实 `text_delta` 增量，2 项组件测试）；`research/chat.py` 对话循环（工具回合上限、流式回答、论断逐条校验、可选评审，5 项组件测试，含引文失败与回合上限）；`parse_claims` 提为公共接口 |
| ④ 前端对话视图与 E2E | **已完成** | 

验证：`make check` 退出码 0（231 项，结构 0 失败，pylint 10.00）；`make coverage` 退出码 0（行 98.9%、分支 92.7%、改动行 100%）。

范围变更记录：`tests/integration/test_migrations.py` 固定了迁移清单，新增迁移后必须更新其期望（已写入第 8 节文件清单）。

### 第 ③ 步前置发现：PI 的真实流式协议

用真实 PI 观测（两次最小调用，未保存推理内容）：

- stdout 的 JSONL 事件序列为 `agent_start` → `turn_start` → `message_start`/`message_end`（system、user）→ 多个 `message_update` → `turn_end` → `agent_end` → `agent_settled`；
- 增量文本在 `message_update.assistantMessageEvent` 内：`{"type": "text_delta", "contentIndex": N, "delta": "..."}`，推理另走 `thinking_delta`（界面上不展示、不落库，遵循 M06 不保存隐藏推理）；
- 因此 SSE 的 `token` 事件可用**真实增量**，无需把完整回答切段伪造流式；`pi_rpc.py` 需新增一个流式变体（async generator 产出 `("delta", text)` 与 `("result", usage)`），`chat.py` 消费它并转发事件。

验证：`make check` 退出码 0（含结构、类型、导入、依赖门槛）；`make coverage` 退出码 0（行 98.6%、分支 91.8%、改动行 100%）。

### 第 ③ 步进展（2026-10-18 第二轮）

- **流式协议**：`pi_rpc.stream_pi` 按 `message_update.assistantMessageEvent.text_delta` 产出增量，末尾给出 `TurnResult`（完整文本 + 用量）；`thinking_delta` 忽略；空闲/墙钟超时仍走 `RunLimitExceeded`。
- **对话循环** `research/chat.py`：三段式（工具回合 → 流式回答 → 论断校验/评审），工具由调用方 `Toolbox` 执行；事件 `tool_call`/`tool_result`/`token`/`citation_check`/`review`/`message_end`；工具结果以 JSON 传给模型（Python repr 不是 JSON，已修正）；引文失败照实上报、`verified` 只数通过的。
- **测试**：2 项流式协议组件测试 + 5 项对话循环组件测试（事件顺序、引文失败、`FORCE_TOOL` 触发回合上限、评审事件、用量累计）；`make check` 251 项通过，`make coverage` 行 98.4% / 分支 91.4% / 改动行 94%。
- **待做**：`api_conversations.py`（REST + SSE + 中止）、`Toolbox` 的真实实现（材料工具 + 题录检索/入库 + 引文校验）、`contracts/openapi.json` 快照、前端视图。

### 第 ③ 步完成（2026-10-18 第三轮）

- `api_conversations.py`：`POST/GET /v1/conversations`、`GET /v1/conversations/{id}`、`POST /v1/conversations/{id}/messages`（SSE）、`POST /v1/messages/{id}/stop`（幂等，已结束的消息返回 `stopped=false`）；事件先落库再推送，`message_end` 的完整回答只写入消息内容、不在事件里重复；PI 配置与限额来自 `EVIDHIST_PI_*`／`EVIDHIST_CHAT_*` 环境变量。
- 路由注册在 `api.py`，契约快照 `contracts/openapi.json` 已更新（+401 行）并通过 `make api-schema-check`。
- 5 项真实 PostgreSQL + 假 PI 的集成测试：会话 CRUD 与事件顺序、`client_message_id` 幂等、已结束消息中止返回未停止、未知会话/消息 404、PI 超时记为 `failed` 且带错误码。
- **真实模型冒烟**（`deepseek-v4.1-flash`，本地 uvicorn + 演示库）：一次提问产生 247 个事件——1 `message_start`、4 `tool_call`、4 `tool_result`、**234 个真实 `token` 增量**、2 `citation_check`、1 `review`、1 `message_end`；用量 12,468/11,964 tokens；评审 verdict=fail，指出三处引文只锁定「京師」二字、不能支撑论断——与史料研究路径同一类问题。
- 据真实运行修两处：`search` 命中补上作品/卷次标签（此前模型只能说「工具结果没有给出作品名与卷次」）；论断提示词要求引文 8-60 字、只锁关键词不算引文。

验证：`make check` 退出码 0（256 项）；`make coverage` 退出码 0（行 98.1%、分支 90.9%、改动行 94%）；`make security` 退出码 0。

### 第 ④ 步完成（2026-10-18 第四轮）

**前端**（DeepSeek 网页版式：左侧会话栏 + 消息流 + 底部输入区）

| 文件 | 内容 |
| --- | --- |
| `src/domain/chatContract.ts` | 会话/消息/事件契约（zod）；未知事件种类保留、界面安全忽略 |
| `src/api/chat.ts` | REST 调用 + `fetch` 流式读取；SSE 解析为纯函数（可单测），非法 payload 丢弃 |
| `src/components/chat/ChatView.tsx` | 三个 hook（会话列表/消息/一轮生成）+ 子组件；复用项目既有 `useLoad` |
| `ConversationList.tsx` / `MessageBubble.tsx` | 会话侧栏（新建/切换/收起）、消息气泡（Markdown + 工具卡片 + 引文 + 评审） |
| `ToolCallCard.tsx` / `CitationChip.tsx` | 工具调用折叠卡片；引文点击带出 `PendingQuote` 跳到「论断」视图 |
| `Nav.tsx` / `App.tsx` / `styles.css` | 新增「对话」入口、引文跳转接线、版式与响应式 |

**测试与验证（实际执行）**

- 组件/单元：`chatStream.test.ts`（SSE 解析 9 例）+ `chat.test.tsx`（列表、流式回答、工具卡片、引文跳转、中止、失败重试 5 例）+ `chatParts.test.tsx`（小组件 9 例）
- `make frontend-check` 退出码 0：127 项测试，覆盖率行 97.95% / 分支 90.29%（门槛 90%）
- `npm run e2e`：**8 项通过**，新增对话用例（建材料 → 进对话 → 新建会话 → 提问 → 看到流式回答与工具卡片 → 点引文跳到论断视图）；e2e 后端固定使用仓库内假 PI，不调用真实模型
- 后端：`make check` 256 项、`make coverage` 行 97.9% / 分支 91.0% / 改动行 94%

**修复的真实缺陷**

- 客户端中止只断开连接会让消息永远停在 `streaming`：前端改为先调 `POST /v1/messages/{id}/stop` 再断开；后端补 `asyncio.CancelledError` 兜底把消息收尾为 `stopped`
- 引文载荷缺作品/卷次（界面只能显示 UUID）：后端补 `work`/`volume`
- 假 PI 的论断分支只认 `exact_quote`，检索命中给的是 `quote`：放宽匹配，e2e 与组件测试因此可用

**与方案的差异（保留记录）**

1. 引文以消息下方的可点击卡片呈现，**未实现正文内联标记**（方案第 7 节的「可点击标记」按卡片落地）。
2. E2E 用例放在 `frontend/tests/e2e/chat.spec.ts`（方案写的是 `frontend/tests/component/chat.test.tsx` 的补充，实际另建了 `chatParts.test.tsx`）；SSE 接口测试放在 `tests/integration/test_chat_api.py`（需要真实数据库）。
3. `playwright.config.ts` 增加假 PI 环境变量（方案文件清单外，为实现确定性 E2E 的必要改动）。

### 2026-10-19 界面调整：只保留对话作为主界面

按用户要求模仿 DeepSeek 网页版排版，并把材料／论断／引文定位工具的页面与导航按钮从界面隐藏：

- `App.tsx` 只渲染 `ChatView`（`Nav.tsx` 删除）；品牌移入会话侧栏，页面标题改为「EvidHist 对话」。
- 侧栏：品牌行 + 收起按钮、圆角「开启新对话」、会话按「今天／昨天／7 天内／30 天内／更早」分组（`conversationGroups.ts`，4 项单元测试），标题超长省略。
- 主区：空态为居中问候「你好，让我们开始聊天吧」+ 说明 + **紧随其下的圆角输入区**；有消息后输入区固定底部。输入区含提示文案与圆形发送/中止按钮；消息气泡、工具折叠卡片、引文卡片照旧。
- 引文卡片改为**只读展示**（不再跳转到论断视图，因为该视图已隐藏）；`onUseQuote` 链路从对话组件移除。
- 工作台视图（材料／论断／引文定位工具）代码与测试保留，但不再有界面入口：
  - `appViews.test.tsx` 改为最小测试外壳（仅在测试中组装 SourcesView + ClaimsView），继续覆盖「选中引文 → 绑定证据」；
  - `tests/e2e/workbench.spec.ts`、`locate.spec.ts` 以 `test.skip` 标注「视图当前隐藏」；对话 E2E 断言主界面没有这三个入口。

验证：`make frontend-check` 退出码 0（132 项，行 97.7% / 分支 90.3%）；`npm run e2e` 退出码 0（1 通过、7 跳过）；截图核对空态与对话态排版。

### 2026-10-19 展示调整：引文只呈现材料·卷次与原文

按要求不再把内部标识暴露在回答里：

- 后端 `answer_prompt`：出处写法改为「材料名·卷次」+ 逐字原文，并明确「正文里不要出现内部标识
  （version_id、UUID、编号）与码点区间等数字」；原先要求「依据（作品/卷次/区间）」的措辞已删除。
- 前端引文卡（`CitationChip.tsx`）：只显示原文 + `材料·卷次` + 校验结果；缺标签时显示「出处未标注」，
  不再回退到 UUID 前缀，也不再显示码点区间。
- 前端工具卡（`ToolCallCard.tsx` + `ToolResultView.tsx` + `toolLabels.ts`）：折叠展开后按工具给出
  可读结果——检索命中列「材料·卷次 + 原文 + 上下文」，材料清单列「材料·卷次 + 字数」，题录列标题与
  年份/刊物，`verify_citation` 只给「通过程序校验／未通过：原因」；参数行只显示检索词、原文或已知版本
  的「材料·卷次」，不再打印原始 JSON。界面通过 `toolLabels` 把版本编号映射为标签，编号与区间不上屏。
- 顺带修掉一个真实缺陷：`text()` 只接受字符串，导致题录年份（数字）被丢弃、`2019 · 明史研究` 只剩刊物名。

验证：`make check` 退出码 0（257 项）；`make coverage` 退出码 0（行 97.9% / 分支 91.0%）；
`make frontend-check` 退出码 0（145 项，行 97.85% / 分支 91.91%）；`npm run mutation` 退出码 0
（160 变异全杀）；`npm run e2e` 退出码 0（对话用例通过）；截图核对引文卡显示「于謙 / 明史·卷11 · 通过程序校验」。

### 2026-10-19 真实模型试验：显示治理的端到端验收

**试验设置**：演示库（`evidhist_demo`，3 份材料 / 25 卷 / 6 论断 / 7 证据），真实 PI
（`deepseek-v4.1-flash`，wall 180s），问题「于謙在北京保衛戰中的作用是什麼？」，经 HTTP SSE 落库后
再用浏览器打开同一会话截图核对。

**新会话（新提示词）**

| 指标 | 结果 |
| --- | --- |
| 事件 | 1 message_start、4 tool_call/4 tool_result、**253 个真实 token 增量**、5 citation_check、1 review、1 message_end |
| 正文长度 | 739 字符 |
| 禁用模式 | `version_id` 0 处、UUID 0 处、「区间+数字」0 处、裸区间数字 0 处 |
| 引文 | 6 条，长度 31/23/29/30/25/16 字（均在 8–60 内），全部为 `明通鑑·卷029` |
| 界面 | 正文以「——明通鑑·卷029」标注出处，引文卡显示「明通鑑·卷029 · 通过程序校验」，无需隐藏任何内容（提示条未出现） |
| 评审 | verdict=fail（意见为「建议补充说话人或奏疏归属」等 info 级提示，非引文错位） |

**旧会话（旧提示词已写死标识与区间）**

| 指标 | 结果 |
| --- | --- |
| 正文 | 渲染前隐去 13 处内部编号/码点区间，末尾如实显示「已隐藏 13 处内部编号或码点区间。」 |
| 表格 | 「区间（字符）」整列移除，标题「依据（作品／卷次／区间）」改写为「依据（材料·卷次）」 |
| 引文卡 | 依靠读取时补标签，显示「明史·卷167」「明史·卷168」「明史·卷172」「明通鑑·卷029」等（此前是「出处未标注」） |
| 渲染文本 | 无 UUID、无 `version_id`、无码点区间 |

**实现要点**

- 后端 `GET /v1/conversations/{id}` 读取时用 `_version_labels` 查 `text_versions`+`sources` 标签，再由
  `_labelled_payload` 为旧事件的引文补齐 `work`/`volume`（不读正文，不改进库数据）。
- 前端 `cleanAnswerText`（`answerText.ts`）：移除整段 id 映射括号、完整与截断 UUID、`version_id` 标记、
  带「区间/码点/偏移」字样的起止数字与闭区间记法；移除表头含「区间/码点」的整列；清理残留标点。
  改动处数由 `MessageBubble` 以 `已隐藏 N 处…` 一行小字如实说明（不静默改写历史）。
- 试验脚本与截图：`.cache/real_trial.py`、`.cache/shot-real-new.png`、`.cache/shot-real-old.png`。
