# 夜间 Goal 状态：前后端对齐 v0.1

本文件是 [夜间任务](night-goal-fullstack-2026-10-09.md) 的断点续传记录。上下文压缩后从这里继续，不重新设计。

## 计划（2026-10-09 23:10 建立）

时间预算（Asia/Shanghai）：23:10 开始，07:30 冻结功能，08:00 截止。提交只能在 08:00 前完成（10-10 为调休工作日，09:00–18:00 禁止提交；夜间窗口合法）。

| 阶段 | 内容 | 目标时间 |
| --- | --- | --- |
| P0 | 冻结 API 契约与 DB 模型；本文件记录 | 23:40 |
| P1 | 后端 TDD：领域单元 → 迁移 runner + 真实 PG 集成 → API + 系统测试 | 01:40 |
| P2 | 前端子 Agent（subagent_fork，仅拥有 frontend/**）实现工作台；主 Agent 并行做后端深测 | 04:00 |
| P3 | 合并前端、修复、E2E 真实全流程（含刷新回查与重启持久验证） | 05:30 |
| P4 | 全量门槛（make check/coverage/mutmut/Stryker/frontend-check/audit） | 06:30 |
| P5 | 独立审阅子 Agent（只读）+ 修复记录 | 07:10 |
| P6 | 演示环境（持久卷 demo DB + seed + 启停）、v0.1-delivery.md、提交 | 07:55 |

## 已冻结的契约（P0 结论，详见 contracts/openapi.json）

资源：
- `POST /v1/sources`：创建材料（标题/来源说明/使用条件）+ 初始文本版本；同标题+同内容散列重复提交返回既有版本（幂等）。
- `GET /v1/sources?q=`：列表+基本查找；`GET /v1/sources/{id}`：详情含版本列表。
- `POST /v1/sources/{id}/versions`：新增不可变版本（内容散列去重；编辑文本=新版本，旧版本与旧引用可回查）。
- `POST /v1/versions/{version_id}/locate`：按持久版本校验区间与字句（产品主流程）；`POST /v1/quotes/locate` 保留为显式文本工具语义。
- `POST /v1/claims`（论断，语句自然幂等）；`GET /v1/claims`、`GET /v1/claims/{id}`（含证据列表）。
- `POST /v1/claims/{id}/evidence`：绑定证据（版本+区间+关系 支持/反对/提及/证据不足+说明），自然键幂等。

DB（PostgreSQL，SQL 迁移文件 + schema_migrations 表）：
- sources(id uuid, title, origin, usage_terms, created_at, updated_at)
- text_versions(id uuid, source_id→sources, label, content, content_sha256, created_at, UNIQUE(source_id, content_sha256))
- claims(id uuid, statement, review_status 默认'未核查', created_at, UNIQUE(statement))
- evidence(id uuid, claim_id→claims, version_id→text_versions, start int≥0, end int>start, relation, note, created_at, UNIQUE(claim_id, version_id, start, end, relation, note))

定位/校验错误码沿用 domain：version_mismatch / invalid_range / quote_mismatch；新增 404：source_not_found / version_not_found / claim_not_found；幂等命中不算错误（200 返回既有资源）。

边界不变量（测试先行）：
1. 不存在版本 → 404 version_not_found；不存在材料 → 404 source_not_found。
2. 空/越界/反向区间 → 422 invalid_range；字句不符 → 422 quote_mismatch。
3. 重复原句按（start,end）确定性定位，无歧义。
4. 扩展汉字（𠀀 等）按 Unicode 码点计数，UTF-16 转换在 domain/offsets.ts 集中处理（前端选区→码点）。
5. 版本更新产生新版本后，旧证据仍按旧版本回查。
6. 重复提交（同自然键）不产生重复业务行。
7. 服务重启后数据仍可回查（系统层：起两个服务实例先后读同一 DB）。
8. 同文不同出处仍是两个材料，不合并、不显示独立性确认。

## 进度记录

- 23:09 goal 启动；基线为 09f068d（README/frontend/后端门槛均已提交，工作区干净）。
- 23:10 本计划建立。下一步：写契约 OpenAPI + 后端 TDD。
- 23:23 **P0+P1 后端完成**：migrations/0001_init.sql + db_migrations.py runner；models/db/sources_service/claims_service/store_errors；api_sources + api_claims 路由（幂等 201/200、404/422 稳定码）；materials 领域（内容散列/关系词表）。测试：单元 13（materials）、集成 29（业务存储 + HTTP 边界 + 全新库迁移顺序/幂等）、系统 4（真实服务重启后回查、真实 HTTP 幂等不重复）。make check 通过；coverage 162 项独立行 98.41%/分支 96.34%。契约快照已冻结并验证导出幂等。CLI：scripts/migrate.py（含 --dry-run）、scripts/demo_database.py（持久卷 55433）、scripts/seed_demo.py；Make 目标 migrate/demo-*。
- 23:32 前端子 Agent d7fc8a3b 启动（仅拥有 frontend/**），实现工作台视图；主 Agent 并行做 mutmut 全新运行与后端收尾。
- 23:34 mutmut 全新运行：32/32 杀死（编解码器名大小写 4 个等价变异以 `# pragma: no mutate` 逐项排除并注释理由；错误消息细节用测试钉死）。
- 23:38 **演示环境验证完成**：`make demo-up`（持久卷容器 55433，修正 PG18 挂载点到 /var/lib/postgresql）→ `demo-migrate`（全新库应用 0001）→ `demo-seed`（2 材料/1 论断/2 证据）→ `demo-run`（服务 8000，/health/ready 200）→ 容器与服务**全部重启后**数据仍完整（2/1/2）。测试 DB 容器仍在运行（集成/系统测试用）。
- 已知偏差：pyproject 的 allowed-confusables 增加全角括号（中文排版需要，属配置策略微调）；mutmut only_mutate 扩展至 domain/materials.py；demo 容器挂载点按 PG18 官方建议。

- 00:14 前端子 Agent 交付：95 项测试、覆盖 97.22/91.21/93.78/96.65、Stryker 144/144 零幸存、lint/type/format/api-types 全绿。主 Agent 复核确认。
- 00:38 **P3 合并+修复完成**：E2E 7 项通过（完整产品流含刷新回查、幂等重试、手动绑定 422、工具视图 𠀀/版本不符/axe/键盘）。过程中发现并修复两个真实缺陷：① 前端选区切开代理对可产生孤立代理字符 → 引文按码点对齐（VersionTextArea）+ 后端 422 安全渲染（api.py validation handler，组件回归用例）；② E2E 选区修正为 [4,6)。
- 00:40 **P4 全量门槛**：make check ✓（快速 138）；集成 29 ✓；系统 4 ✓；覆盖 168 项独立行/分支 100%/100%；mutmut 32/32；Stryker 144/144；安全 0 发现（pip-audit/Semgrep/npm audit）；fixture 4/4；演示重启存活。
- 00:42 独立审阅子 Agent（4ec8f52a，只读）启动；主 Agent 并行完成 v0.1-delivery.md 填实、development.md/README v0.1 状态更新。待审阅结论 → 修复 → 提交。

- 00:5x **P5 独立审阅完成并修复**（审阅者 4ec8f52a，只读，未改文件）。发现 1 严重 3 中等 7 轻微 3 建议。已修复：S1 补真实“重复原句”用例（集成：甲乙甲丙两处绑定不合并；E2E 全流程改为 𠀀 两处）；M1 models 补 claims 唯一约束；M2 限制条目如实改写（sources 无唯一约束并发可重复、其余并发为 500）；M3 migrate.py 单事件循环 + 无 URL 拒绝猜测退出 2；L2 ilike 转义 %/_（含回归测试：搜索 % 与 _ 返回空）；L4 docstring 修正；L5 assert 改显式 raise；L6 补“新版本后旧证据回查”用例；L3/A1 修文档错误码枚举与 .txt 导入坏编码提示（U+FFFD 检测）。L1 提交后核实。A2/A3 记录为后续。

- 00:48 **收尾**：三笔主题提交（后端 82b2434 / 前端 b7254f2 / 文档 47f7ab1），工作区干净；mutmut 32/32 与 Stryker 144/144 在审阅修复后重跑确认；测试库容器已清理；演示库（持久卷）与演示服务（8000，PID 1750）按交付文档保留运行。夜间任务七个完成条件均有实际执行证据，见 v0.1-delivery.md。

（本 Goal 收尾完成。）
