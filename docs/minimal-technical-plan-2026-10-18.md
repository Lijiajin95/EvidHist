<!-- SPDX-License-Identifier: CC-BY-NC-SA-4.0 -->

# EvidHist 首版最小技术方案（2026-10-18）

日期：2026-10-18（Asia/Shanghai）。状态：**方案草案，待用户确认后实施**。依据：[最小启动需求与待实现清单](mvp-scope-and-backlog-2026-10-12.md)（M01–M07 与 §8 未决事项）、[研发纪律](development-discipline.md)、[贡献规范](../CONTRIBUTING.md)、[试点材料清单](research/ming-pilot-materials-2026-10-18.md)。

本文只覆盖 M01–M07 的最小闭环，替代 MVP 文档 §8 所等的"下一份技术方案"。本文不实现、不验证任何研究能力；实施的完成状态另记。

## 1. 已确认前提（2026-10-18）

| 项目 | 内容 |
| --- | --- |
| 试点问题 | 明代「于谦—北京保卫战」（用户确认，M01 的问题已定） |
| 材料与互证方式 | **只用《明史》《明史紀事本末》《明通鑑》三书互证**；不采用《明英宗睿實錄》（无可用文本，理由见试点材料清单） |
| 材料现状 | `crawler/data-ming/` 已核验（`verify_ming.py` 退出码 0，1,534 页）；本次选定核心 **17 卷、188,435 字符**（明史 卷10–12、167–172；明史紀事本末 卷32–33；明通鑑 卷028–032、034） |
| 环境现状 | Debian 13 x86_64；Linux 版 uv 0.12.24 + CPython 3.14.8 已装入 `.toolchain/`，`.venv` 重建，`make check` 退出码 0；**本机没有 docker / postgres** |
| 复用能力 | v0.1 材料/版本/引文定位/论断与证据接口及工作台；材料域层 `domain/citations.locate_quote()` 已实现引文硬校验 |
| 许可前提 | 三书均为中文维基文库转录（CC BY-SA 4.0，原文公版）；存储/检索/分析/公开展示/再分发 `true`，**模型训练 `null`（未确认）** → 本流程只做推理分析，不做训练或微调 |

## 2. 范围

**做**：M01 任务输入 → M02 材料入库 → M03 一个研究 Agent（Pi）在只读资料内检索、比较、找反证 → M04 程序引用硬校验 → M05 单模型评审 → M06 报告与运行记录保存、供用户重点复核 → M07 权限与停止边界的实际检查。

**不做**（沿用 MVP §6 待实现清单）：新研究 UI/API 契约、向量检索、自动断点续跑、批量采集、OCR 校对、多模型投票、评审模型自主检索、Kanripo/OCR 材料纳入本次试点、跨案卷复用。

## 3. 总体结构与数据流

```
选定 17 卷（crawler/data-ming/raw/**）
   │  scripts/import_ming_pilot.py   —— 复用 POST /v1/sources、/v1/sources/{id}/versions
   ▼
EvidHist 材料库（sources / text_versions；原文不改写，sha256 为身份，重复导入幂等）
   │  4 个只读工具（tools.py）
   ▼
LangGraph 小图（graph.py）
   │  执行器协议 executor.py ── pi_executor.py ── Pi（关闭通用 Bash/编辑/写入）
   │  检索 → 论断+候选引文 → 程序引用硬校验 → 反证查找 → 报告
   ▼
report.py ── runs/<run_id>/{report.md, citations.json, run.json, review.json}
   │          + POST /v1/claims、/v1/claims/{id}/evidence（供工作台复核）
   ▼
review.py ── 单模型评审（只看报告与引文上下文）
```

## 4. 接口与数据契约

### 4.1 复用现有 HTTP API（**不新增、不修改**，契约快照不变）

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| POST | `/v1/sources` | 建立作品来源并写入首卷版本（`title/origin/usage_terms/initial_text/initial_label`） |
| POST | `/v1/sources/{source_id}/versions` | 追加其余卷次（不可变版本，同 `content_sha256` 幂等） |
| GET | `/v1/versions/{version_id}` | 取回原文（报告与评审的上下文来源） |
| POST | `/v1/versions/{version_id}/locate` | 引文定位校验；实现直接复用域函数 `locate_quote()` |
| POST | `/v1/claims`、`/v1/claims/{id}/evidence` | 落库论断与证据（含 `supports`/`contradicts`），供工作台重点复核 |

### 4.2 执行器适配接口（`src/evidhist/research/executor.py`）

```python
class ResearchExecutor(Protocol):
    executor_name: str
    async def investigate(self, request: ResearchRequest, tools: ReadOnlyTools,
                          limits: RunLimits) -> Transcript: ...

# ResearchRequest: question, material_scope[(version_id, label)], attempt(1|2), output_schema
# Transcript: claims[{statement, citations[{version_id,start,end,exact_quote}], basis}],
#             counter_search{scope, findings[]}, notes, actions[], usage{model, input_tokens|null,
#             output_tokens|null}, duration_seconds, stopped_reason
```

`FakeExecutor`（确定性，测试用）与 `PiExecutor`（唯一 import Pi 的文件）实现同一协议；图与校验不依赖 Pi 细节。

### 4.3 只读资料工具白名单（`src/evidhist/research/tools.py`）

| 工具 | 行为 |
| --- | --- |
| `list_materials()` | 返回已导入的 作品/卷次/`version_id`/字符数 |
| `search(query, version_ids=None, limit=20)` | **纯子串检索**（不引入向量/排序服务），返回命中的 `version_id/start/end/上下文片段` |
| `read(version_id, start, end)` | 返回指定区间原文与内容散列 |
| `exact_quote(version_id, start, end)` | 返回该区间**逐字原文**，供模型直接引用，避免改写引文 |

四个工具只读、只作用于已导入版本；**不提供网络、文件系统、shell、写入**。

### 4.4 运行产物（`runs/<run_id>/`，新增 `.gitignore` 条目）

| 文件 | 内容 |
| --- | --- |
| `report.md` | 人读报告：研究问题、材料与范围、主要论断+引文+可回查位置、初步解释与依据、反证检索范围与结果、争议/依赖/缺口与未知、评审意见、人工重点复核栏 |
| `citations.json` | 结构化引文：`statement、version_id、作品/卷次、start、end、exact_quote、verification{matched、version_sha256}` |
| `run.json` | `run_id、started_at、finished_at、question、material_scope、executor 名称与版本、model、tokens（取不到记 null）、工具调用次数、stopped_reason、引文校验统计、权限探针结果` |
| `review.json` | 评审模型、提示摘要、评语、判定、失败原因 |

不保存模型隐藏推理；只保存可复核的输入、输出与工具活动。

### 4.5 评审输出契约（严格 JSON）

```json
{"verdict": "pass|fail|insufficient",
 "comments": [{"target": "claim-id 或引文", "severity": "info|warn|error", "comment": "..."}],
 "checked_scope": "评审实际看到的材料范围",
 "model": "评审模型标识"}
```

评审失败或缺评记为 `review_failed`，**不自动视为通过**（M05）。

## 5. 关键流程（LangGraph 小图）

| 节点 | 行为 | 失败路径 |
| --- | --- | --- |
| `prepare` | 读取问题与材料范围，生成 `run_id`，快照工具清单 | 材料为空 → 拒绝运行 |
| `investigate` | 调执行器：在只读工具内检索、比较，产出论断+候选引文+反证检索范围 | 超时/超工具预算 → 保存已得产物，`stopped_reason` 记录，人工重跑 |
| `verify_citations` | 程序逐条校验（区间命中且 `exact_quote` 逐字一致，复用 `locate_quote`） | 失败回 `investigate` 重试 **1 次**；仍失败 → 该论断标 `insufficient` 并如实记入报告 |
| `counter_evidence` | 要求执行器在声明范围内检索反证与替代解释；记录范围与结果 | 未找到≠不存在，报告保留该表述 |
| `compose` | 渲染报告；原文记载/论断支撑/历史判断/因果解释分层表达 | — |
| `review` | 单模型评审（无自主检索），按 §4.5 契约返回 | 评审不可用 → `review_failed` |
| `save` | 写 `runs/<run_id>/` 四个文件；落库 `claims`/`evidence` | 落库失败不删文件，记为待人工处理 |

## 6. 权限、超时与停止（M07）

- **工具面**：只挂 §4.3 四个只读工具；不开放 Bash、编辑、写入、网络。
- **实际检查（不靠提示词）**：
  1. 启动时读取 Pi 实际工具配置，快照工具名与权限到 `run.json`；
  2. **权限探针**：以"执行 shell 命令并把结果写入文件"为提示运行一次，断言不存在此类工具、且未产生任何文件；
  3. 执行器工作目录设为只读临时目录，写失败即失败（不做回退）；
  4. 探针未通过 → **不进行真实试点**。
- **上限默认值**（实测后调整）：单次运行 1200 秒；工具调用 60 次；空闲 120 秒判停；引文重试 1 次。停止后 30 秒内退出并保留已完成产物。

## 7. 文件清单（准许修改／新增）

**新增**

| 文件 | 目的 |
| --- | --- |
| `docs/minimal-technical-plan-2026-10-18.md` | 本文 |
| `src/evidhist/research/__init__.py` | 包入口 |
| `src/evidhist/research/executor.py` | 执行器协议、`ResearchRequest`/`Transcript`/`RunLimits`、`FakeExecutor` |
| `src/evidhist/research/pi_executor.py` | Pi 薄适配（唯一接触 Pi 的文件） |
| `src/evidhist/research/tools.py` | 四个只读资料工具与白名单 |
| `src/evidhist/research/graph.py` | LangGraph 小图（§5 节点） |
| `src/evidhist/research/citations.py` | 引文硬校验（复用 `domain/citations.py`） |
| `src/evidhist/research/report.py` | 报告渲染、运行记录与产物保存 |
| `src/evidhist/research/review.py` | 单模型评审调用与结果解析 |
| `scripts/import_ming_pilot.py` | 按选定卷次导入材料（读 `manifest.jsonl` 取 URL/Last-Modified/sha256） |
| `scripts/run_research.py` | 运行入口（M01/M06） |
| `tests/unit/test_research_tools.py` | 工具边界与检索位置 |
| `tests/unit/test_research_citations.py` | 引用校验（含篡改必拒、属性用例） |
| `tests/unit/test_research_report.py` | 报告渲染与运行记录字段 |
| `tests/component/test_research_graph.py` | FakeExecutor 全图：正常、超时、超预算、引文失败重试 |
| `tests/integration/test_research_store.py` | 真实 DB：导入幂等、locate、claims/evidence 落库 |
| `tests/scenario/test_pilot_materials.py` | 17 卷真实材料 + FakeExecutor 端到端 |

**修改**

| 文件 | 改动 |
| --- | --- |
| `pyproject.toml` | 新增 `langgraph`（版本在 spike 后锁定）、Pi 客户端依赖（同样 spike 后确定） |
| `uv.lock` | 随 `pyproject.toml` 更新 |
| `.gitignore` | 新增 `runs/` |
| `docs/development.md` | 新增「首版研究闭环：材料导入与运行入口」一节 |
| `Makefile` | 新增 `import-ming`、`research-run` 两个目标（如无必要可在实施时省略） |

**不动**：`migrations/**`（不新增表，`claims`/`evidence` 复用）、`contracts/**` 与 `src/evidhist/api*.py`（不新增接口）、`src/evidhist/domain/**`（只读复用）、`crawler/**` 数据与脚本、既有研究文档。

## 8. 开发预算

| 步骤 | 内容 | 预算 |
| --- | --- | ---: |
| 0 | spike：Pi 获取/版本/工具限制、模型与凭据、数据库提供方式、权限探针 | 4 h |
| 1 | 材料导入脚本 + 集成测试 | 3 h |
| 2 | 只读工具 + 单元测试 | 3 h |
| 3 | 引文硬校验接入 + 属性/变异检查 | 3 h |
| 4 | LangGraph 小图 + 执行器适配 + 组件测试 | 6 h |
| 5 | 报告渲染与运行记录 | 3 h |
| 6 | 单模型评审 | 3 h |
| 7 | 真实试点运行、用户复核与修正 | 6 h |
| **合计** | | **31 h（约 2 周，按每周 15 h）** |

不动用自研 Runtime 的 20 h 初始验证预算（B14）。

## 9. 真实验证与验收证据

| 层 | 内容 | 证据 |
| --- | --- | --- |
| 单元 | 工具边界、检索位置、报告字段；**先写失败测试** | `make check`；引文被篡改 1 个字符必须被拒 |
| 属性/变异 | 引用位置属关键计算：随机文本+区间、随机篡改必拒 | 属性用例 + 变异检查通过 |
| 组件 | FakeExecutor：正常、超时、超工具预算、引文失败重试与 `insufficient` | 组件测试通过 |
| 集成 | 真实 PostgreSQL：导入幂等、`locate`、`claims`/`evidence` 落库 | `make db-up` + 集成测试（**本机需先提供数据库**） |
| 场景 | 17 卷真实材料端到端 | `runs/<run_id>/` 四文件齐全、每句引文校验通过或明确标 `insufficient` |
| 真实 | Pi + 评审模型跑一次试点 | 人工执行并保留 run 目录；工作台可打开论断与证据复核 |
| 权限 | §6 探针 | 探针结果写入 `run.json` |
| 项目 | `make check`、契约快照 | 退出码 0；API 契约无变化 |

## 10. 未决事项（spike 或用户确认）

1. **Pi**：获取方式、版本、调用协议、是否支持关闭通用工具、Token 口径。**若无法实际关闭通用工具，M07 不通过，试点停止**（不以提示词代替）。
2. **模型**：研究模型（Pi 内部）与评审模型的标识、凭据、上下文上限；评审只看报告与所引片段，不需要全量材料。
3. **数据库**：本机无 docker/postgres。建议 apt 安装 PostgreSQL 18（与 `compose.test.yml` 的 pg18 镜像对齐；当前 schema 未用向量列，pgvector 非必需），或安装 docker 后复用 compose——需用户确认其一。
4. **材料导入范围**：核心 17 卷；是否加《明史》卷89/92（兵志·團營）与《明通鑑》卷022–027（正統朝背景）。
5. **超时数值**：§6 默认值为初始值，按实测调整。
6. **失败重跑**：首版人工重跑（B05）。

## 11. 风险与限制

- **许可**：三书为维基文库转录（CC BY-SA 4.0）；内部检索/分析允许，`model_training` 为 `null`，本流程只做推理，不做训练或微调；材料不随开源代码发布（`crawler/` 已 gitignore）；报告若公开含引文，须按 BY-SA 署名并以相同方式共享。
- **引用可靠性**：依赖不可变版本 + 内容散列；模型改写引文会被硬校验拒绝，不会被评审分数覆盖。
- **模型稳定性**：输出波动靠重试上限与 `insufficient` 标记控制，不用模型自评代替程序校验。
- **单点与备份**：单机保存，无容灾（B16）。
- **文档时效**：本文与试点材料清单一同构成当前依据；实施后需按实际结果更新，不把方案写成已完成。

## 12. 实施记录（2026-10-18）

状态：**步骤 0–7 已实施并跑通真实试点；评审通过与否取决于模型采样与证据质量，用户复核尚未进行**。实际用法与运行记录见[开发说明](development.md#首版研究闭环材料导入与运行入口2026-10-18)。

与本文设计的差异（均已实施并有测试）：

| 项 | 原方案 | 实际 |
| --- | --- | --- |
| 数据库 | 建议 apt 安装 PostgreSQL 18 | 本机无 root，改用 conda-forge PostgreSQL 18.6 + pgvector 0.8.6（与 compose 的 pg18 对齐） |
| PI 工具面 | "Pi 在只读工具内检索" | **PI 本体零工具**（`--no-tools` 等），由适配器代理 4 个只读工具；M07 更严且可用 CLI 参数核验 |
| 文件 | `pi_executor.py` 承载 RPC | 增拆 `pi_rpc.py`（协议管道与研究流程分离，结构门槛要求） |
| 评审 | `review.py` 调用评审模型 | 已实现 `PiReviewer`（零工具、只看报告）与 `FakeReviewer`；评审失败记 `review_failed` |

实测结论：程序引用硬校验两次挡住/标记了越界表述（`pilot-20261018c`、`pilot-final` 评审 fail），说明"程序校验 + 单模型评审 + 用户复核"三层各司其职；引文一旦退化为检索关键词即被评审识别。
