# 开发与检查说明

设计与配置目标基线：**Python 3.14.8、uv 0.12.24**、**Node 26**（本机实测 26.7.0；AGENTS.md 已把前端基线从 24 更新为 26）、Docker（真实数据库测试使用）。项目定位为个人开源产品。首次执行需要下载锁定依赖与测试镜像；格式、单元、属性、组件和场景测试随后可离线运行。Python 支持范围与工具兼容性由 `pyproject.toml` 及 `uv.lock` 约束；前端依赖由 `frontend/package-lock.json` 锁定（lockfileVersion 3）。

**基础入口已复核，完整验收仍需补齐。** 本次在 3.14.8 上执行 `make check` 已通过 76 项快速测试、类型、API 快照与策略配置检查，基础解释器也已指向持久目录。数据库、系统、变异、安全和新检查方案分别验证；不能将旧 3.12 的通过记录当作全部新基线结果。任务见[交接清单](coding-agent-handoff-2026-10-09.md)。

先准备 uv 0.12.24 或更新的兼容版本；旧 uv 0.12.5 未包含 Python 3.14.8 下载条目。当前开发组也锁定了 uv，Make 优先使用 `.venv/bin/uv`，保持本地与 CI 的工具版本一致。

托管 Python 位于项目 `.toolchain/python`，虚拟环境放入 `.venv`；两者都被 Git 忽略。本次只读复核确认 `.venv` 基础解释器已绑定该持久目录。运行环境依赖这两个目录，清理解释器后需要重建虚拟环境。

## 初始化与日常检查

```bash
make setup
make hooks
make check
```

`make setup` 安装锁文件中的开发、变异与安全依赖到项目 `.venv`；`make hooks` 安装 pre-commit、commit-msg 与 pre-push。CI 使用同样的检查入口，自动格式修复用 `make format`。

提交消息遵循[贡献规范](../CONTRIBUTING.md)。北京时间法定调休工作日 09:00–18:00 禁止提交；设计要求 pre-commit 与 commit-msg 都检查真实时钟，CI 复核新增 Git 时间戳。对应草稿及 hooks 已提供，新规则仍待验收。`make commit-policy-config` 用于检查策略与日历，缺失年度日历在该时间窗口内拒绝提交。

`make check` 还会检查 API 契约快照，修改接口后执行 `make api-schema` 并审阅兼容影响。前端工程与首个真实界面已于 2026-10-09 夜间落地，入口见[前端工程](#前端工程)一节；可靠性方案背景见[设计文档第 16 章](architecture-analysis-2026-10-09.md#16-前端产品工程可靠性方案)。

## 真实数据库与系统测试

```bash
make db-up
make test-integration
make coverage
make test-system
make db-down
```

启动脚本使用基础 Docker 命令，不依赖 Compose 插件；镜像从 `compose.test.yml` 读取。容器只绑定 `127.0.0.1:55432`，数据库名为 `evidhist_test`，数据放在临时文件系统。清理脚本校验项目标签后才删除自己的测试容器。需要 Compose 的环境也可以直接使用该配置，完成后通过 Compose 清理它启动的资源。

数据库测试缺少 DSN 或目标不是测试数据库时直接失败。可通过 `TEST_DATABASE_URL` 为 Make 目标显式配置测试连接；修改容器端口时同步设置 `EVIDHIST_TEST_PORT` 和连接 URL。示例账号只用于本地隔离测试。

覆盖门槛为 `src/evidhist` 的行/分支综合覆盖 90%，并由 `scripts/check_coverage_thresholds.py` 按 `coverage json` 原始计数分别核对独立行覆盖与分支覆盖（2026-10-09 夜间实测均为 100%）。无 Git 基线或改动中没有可测行（仅测试/文档）时，增量覆盖按策略标记“不适用”；有基线时由 diff-cover 测量改动行覆盖。真实 HTTP 系统测试启动临时独立进程并在测试后关闭；API 组件测试使用受控数据库边界替身，两种结果分别报告。

## 变异与安全检查

```bash
make mutation
make security
```

mutmut 当前只修改引用定位领域文件，并以两个子进程执行。结果写入 `mutants/mutmut-cicd-stats.json`；门槛脚本 `scripts/check_mutation_stats.py` 读取 `config/quality-policy.toml` 的 `[mutation]` 门槛，拒绝零变异、幸存、未测、超时或未完成结果。调试使用 `.venv/bin/mutmut results`、`show` 或 `browse`。不要把自动生成的 mutant 应用到未保存的业务源码。注意 `mutants/` 是可再生的缓存目录：更换测试集后必须删除它强制重新生成，否则会复用陈旧结果（2026-10-09 已因旧缓存踩过一次，mutmut 的 `also_copy` 同时需要 `config`、`scripts`、`contracts` 供沙箱内测试使用）。

`make security` 审计完整锁定的运行和工程依赖，并执行本地 SAST 规则（**bandit**，属 `security` 依赖组）。漏洞查询需要网络；网络/工具失败意味着未完成检查。规则配置在 `pyproject.toml` 的 `[tool.bandit]`，报告写入 `reports/bandit.json`。当前覆盖危险命令执行、动态 Python 执行、不安全反序列化与关闭 TLS 校验四类模式，并有植入负例测试（`tests/unit/test_security_scan.py`）验证它们确实会被拦下。[Semgrep](https://semgrep.dev) 已于 2026-10-18 替换为 bandit：semgrep 经 `mcp` 引入已知漏洞（CVE-2026-59951）且依赖体积大，而上述四类模式 bandit 原生覆盖。

## 固定评测案例

```bash
make eval-fixture
.venv/bin/evidhist-eval-quotes \
  --cases evals/quotes.jsonl \
  --predictions /absolute/path/to/model-predictions.jsonl \
  --output reports/model-quote-eval.json
```

案例与 fixture 是人工编写的合成数据，覆盖原句、扩展汉字、重复词消歧和材料不足。fixture 运行只验证评分链路；不会发起模型调用或产生真实模型质量结论。

真实预测采用每行 `{"id": "案例ID", "output": Citation对象或null}` 的 JSONL 格式。另保存模型、提示词、检索、语料版本与调用记录。遗漏预测计为失败，重复或未知 ID 使输入无效；评分器检查 Schema、版本、位置和任务预期。

## 本地服务与当前能力

```bash
make db-up
make run
```

服务监听 `127.0.0.1:8000`：`GET /health/live` 检查服务活性，`GET /health/ready` 检查数据库可用性；开发接口文档在 `/docs`。退出服务并完成测试后执行 `make db-down`。

`POST /v1/quotes/locate` 接受显式提供的文本版本和引文，返回经过校验的 Unicode 字符位置及原文。位置以 Unicode code point 计数，终点不包含在引用中。这个基础接口只检查提供文本内的版本与定位关系；权威史料库查找、来源真实性、来源独立性及历史解释属于后续研究能力。

## CI 与后续测试接入

`.github/workflows/quality.yml` 定义质量、依赖/安全、后端变异、前端质量、前端 E2E、前端变异和 commit 策略七个作业，锁定 Action SHA 与数据库镜像摘要；Node 作业固定 `node-version: "26"` 并缓存 npm。尚未发布远程仓库，因此没有远程 CI 执行证据；本地执行结果独立记录。

首个真实界面（引文定位）已接入 Playwright 浏览器测试、关键交互案例和 CI；真实模型连接仍未接入，不产生模型质量结论。业务持久化的首次实现仍需数据库迁移与升级验证（当前 `/v1/quotes/locate` 校验显式提交的文本版本，不查库）。

详细方法论见[架构文档第 12、13 章](architecture-analysis-2026-10-09.md#12-测试方法论用不同层次验证不同承诺)。

## v0.1 业务闭环（2026-10-10 夜间）

「史料与引用工作台」：材料（含不可变文本版本，内容散列为身份、自然键幂等）→ 版本文本选区引文（UTF-16→码点转换在 `frontend/src/domain/offsets.ts`，代理对边界向后吸附且引文按码点对齐防孤立代理字符）→ 后端按持久版本校验（`POST /v1/versions/{id}/locate`）→ 论断与证据绑定（支持/反对/提及/证据不足，界面明示「未核查」不声称史实证实）→ 多来源并列展示，刷新/重启后回查。

- 数据库：`migrations/*.sql` 事务性迁移（`schema_migrations` 记账，重跑安全）；`make migrate` / `scripts/migrate.py --dry-run`。全新库迁移顺序与幂等由 `tests/integration/test_migrations.py` 在临时数据库验证。
- 演示环境：`make demo-up`（持久卷容器 127.0.0.1:55433，PG18 挂载 `/var/lib/postgresql`）→ `demo-migrate` → `demo-seed`（合成材料，明确标注非史籍）→ `demo-run`（8000 端口）。停止 `make demo-down` 保留数据卷。
- 孤立 UTF-16 代理字符：请求含代理字符时后端返回 422（`api.py` 的 RequestValidationError 处理器用 `ensure_ascii` 渲染，避免回显值导致 500）；前端选区按码点对齐从源头防呆。组件回归用例在 `tests/component/test_api.py`。
- 运行入口与验证矩阵详见 [v0.1 交付说明](v0.1-delivery.md)。

## 结构度量与新增质量门槛

```bash
make structure-metrics   # 函数有效行/公开接口/文件物理行 + 审阅提示
make import-lint         # Import Linter：领域不依赖 API/数据库适配器
make deptry              # 依赖声明与分组核查
make pylint              # Pylint R0904/C0302（方法数/文件行数）
make coverage-thresholds # 独立行/分支覆盖门槛（读取 coverage.json）
```

这些都包含在 `make check` 中。`config/quality-policy.toml` 是唯一门槛来源：`[structure]`（含 `review_hints` 提示阈值）、`[coverage]`、`[mutation]`（由 `scripts/check_mutation_stats.py` 消费）、`[property_tests]`（由 `tests/conftest.py` 注册为 `evidhist-local/ci/extended` Hypothesis profile，经 `--hypothesis-profile=` 选择）。结构度量由 `scripts/structure_metrics.py`（AST/tokenize 精确计数）与 `scripts/check_structure_metrics.py`（策略应用与报告）实现，边界口径按交接清单第 8.2 节固定：签名计入、装饰器/空行/纯注释/AST docstring 不计、字符串内 `#` 计为代码、嵌套函数分别检查且保留在外层范围、属性/重载按（接收者,名称）去重。TS/JS 的函数行/复杂度/参数/嵌套/语句/文件行由前端 ESLint 规则执行同值门槛；TS 类公开接口计数顺延到真正出现 TS 类时再接入（报告显式标注，不静默通过）。

已验证的负例（均为可重跑的回归测试）：51 行函数、21 接口、501 文件行（`tests/unit/test_structure_metrics.py`）；复杂度 11 与参数 6（Ruff，`tests/unit/test_quality_gates.py`）；错误架构依赖（Import Linter 拒绝假包契约）、卡死测试被 pytest-timeout signal 模式终止、dev 组依赖无理由导入被 deptry DEP004 拒绝（同文件）；空/幸存/超时/中断变异与缺失报告（`tests/unit/test_mutation_stats.py`）；低独立分支覆盖与缺失覆盖报告（`tests/unit/test_coverage_thresholds.py`）；API 快照受控漂移（`tests/unit/test_api_contract_drift.py`）；前端空变异报告、幸存状态与生成物漂移（`frontend/tests/unit/check-scripts.test.ts`）。

例外记录：`reviewed_exceptions` 每条必须包含 `path/rule/reason/owner/review/recheck`；例外文件仍受 1000 行绝对上限约束。当前已知提示（非阻断）：`tests/system/test_running_service.py` 的 `live_service` 46 有效行、`scripts/check_structure_metrics.py` 302 物理行、`tests/unit/test_structure_metrics.py` 344 物理行。

## 前端工程

```bash
make frontend-setup     # npm install（项目内缓存 .cache/npm）
make frontend-run       # Vite 开发服务器（http://127.0.0.1:5173，/v1 与 /health 代理到后端）
make frontend-check     # format:check + lint + typecheck + api-types 漂移 + depcruise + knip + coverage
make frontend-e2e       # Playwright：真实 uvicorn 后端 + Vite 前端 + axe + 键盘
make frontend-mutation  # Stryker + 原始状态门槛
make frontend-audit     # npm audit（--audit-level=high，审计端点固定官方 registry）
```

目录 `frontend/`：Vite 8 + React 19 + TypeScript 5.9（typescript-eslint 8.71 尚不支持 TS 7，故锁定 5.9.3）；ESLint 9 flat config（jsx-a11y 6.10 尚不支持 ESLint 10，故锁定 9.39）+ react-hooks + 类型化规则；Prettier；Vitest 4.1 + jsdom + Testing Library + user-event + MSW 3 + fast-check 4（含 `interruptAfterTimeLimit(4000, {failOnInterrupt: true})` 插件）；Stryker 10 + vitest runner；Playwright 1.64 + @axe-core/playwright；dependency-cruiser 与 Knip。Stryker 10 的 vitest runner 与 vitest 5 存在运行时变异不触发重跑的缺陷（幸存者虚高），已降级 vitest 4.1.11 解决——这是实测结论，不是理论兼容声明。

浏览器：本地默认安装到 `.cache/ms-playwright`（沙箱限制 `~/Library/Caches` 不可写），`npm run e2e/install:browsers` 内置该默认路径；CI 用 `PLAYWRIGHT_BROWSERS_PATH` 指向工作区同一路径。MSW 组件测试的 fetch 中断在拦截层不保证 DOMException，`src/api/locateQuote.ts` 以信号状态归一化为 AbortError。

前端契约链：`npm run generate:api-types` 从 `../contracts/openapi.json` 生成 `src/generated/api-types.ts` 并复制快照到 `src/generated/openapi.json`（复制件使契约测试可在 Stryker 沙箱内运行）；`npm run check:api-types` 同时校验两者无漂移；`tests/unit/api-contract.test.ts` 断言 Zod 运行时 schema 与快照的字段及约束一致（键 + 长度/整数/非负约束）。首个界面为“引文定位”：显式提供文本版本 + 引文（起止 code point 偏移），提交后返回定位与原文高亮，明确声明只校验所提供文本中的位置与字句，不代表来源真实性或史实已证实。UTF-16/code point 转换集中于 `src/domain/offsets.ts`。

## 初始验证记录：2026-10-09（Python 3.12）

环境为 macOS ARM64、Python 3.12.14、uv 0.12.5；数据库使用固定摘要的 PostgreSQL 18 / pgvector 镜像。以下是当前小型骨架的执行快照，业务范围扩大后应重新验证。

| 检查 | 本次结果 |
| --- | --- |
| pytest | 快速测试 35 项、真实数据库 3 项、真实 HTTP 系统测试 2 项，共 40 项通过 |
| pytest-cov | `src/evidhist` 的 153 条语句与 20 个分支，覆盖率 100% |
| mutmut | 引用定位领域范围生成 27 个变异，27 个全部被杀死，无幸存或异常状态 |
| 变异报告门槛 | 拒绝幸存、空结果、超时及中断的负例验证通过 |
| Ruff / Pyright | 格式与静态检查通过；类型检查无错误、警告 |
| pre-commit | 配置和显式文件检查通过；当前仓库已安装提交、推送 hooks |
| pip-audit | 完整锁定依赖的当前环境审计未发现已知漏洞 |
| Semgrep | 4 条本地规则扫描 10 个源文件，无命中；危险命令与动态执行负例被正确阻止 |
| fixture 评测 | 4/4 合成案例通过，只验证评分链路 |
| 配置与文档 | 锁文件、工作流固定引用及本地文档链接检查通过 |

真实研究 UI、真实模型质量与远程 CI 没有执行结果。测试使用的临时数据库容器已清理，可由 `make db-up` 重新建立。

## 本次新增项的验收状态：2026-10-09

| 新增项 | 已知状态 |
| --- | --- |
| Python 升级 | 3.14.8 的 `make check` 已通过；其他层次与发布安装还需独立记录 |
| 兼容性预检 | 3.14.7 临时环境的原有 35 项快速测试通过；不包含之后新增的提交策略测试 |
| 类型检查 | 本次 Pyright 无错误、警告；之前的问题已不再阻断基础检查 |
| 环境位置 | 基础解释器已指向项目 `.toolchain/python`，需继续验证干净安装 |
| 提交规范 | 配置、日历、实现草稿与测试用例已添加；pre-commit、pre-push、commit-msg hooks 已安装；新策略未全面验证 |
| API 契约 | 当前快照一致性检查通过；故意漂移和兼容性检查另验收 |
| 前端 | 已按交接清单第 5 章落地首个真实界面与全部可靠性工具，验收记录见[交接清单执行记录](#交接清单执行记录2026-10-09-夜间代码-agent) |
| 测试资源 | 本次专用临时数据库容器已清理 |

本会话后续工作限定为文档，代码任务、具体缺口及验收要求已移交到[交接清单](coding-agent-handoff-2026-10-09.md)。

## 维护性门槛接入状态

交接清单第 8–12 节的门槛已由代码 Agent 落地：`config/quality-policy.toml`（结构/覆盖/变异/属性测试统一策略）、Ruff C901/PLR0912/PLR0913、Pylint R0904/C0302、pytest-timeout（30s/signal，系统级单项可 60s 预算）、独立行/分支覆盖门槛、mutmut/Stryker 原始状态门槛、Import Linter 禁止契约、deptry（certifi 显式声明于 dev 组、uvicorn/psycopg 按启动证据例外并逐包注释）、Hypothesis profile、前端 ESLint 同值结构门槛、Promise 规则、dependency-cruiser 循环与越层、Knip、axe 自动检查与 failOnFlakyTests。每项硬门槛均有可发现的负例（见[结构度量与新增质量门槛](#结构度量与新增质量门槛)）。顺延项与理由记录在交接执行记录的“未覆盖”清单。

本次文档方案复核同时运行现有 `make check`：Python 3.14.8，76 项快速测试通过，Ruff/格式/Pyright、API 快照与提交策略配置检查通过。该结果只属于已接入检查，未证明上面的新增工具或阈值已经启用。

## 交接清单执行记录：2026-10-09 夜间（代码 Agent）

环境：macOS ARM64，CPython 3.14.8（`.toolchain/python/cpython-3.14.8-macos-aarch64-none`）、uv 0.12.24、Node 26.7.0、npm 11.19.0（项目内缓存 `.cache/npm`）、Docker 29.7.2、Chromium headless shell 156（Playwright 1.64）。测试数据库为项目专用带标签容器（`evidhist-foundation-postgres`，pgvector/pg18:pg18 固定摘要），验收后已清理。

| 检查 | 实际结果 |
| --- | --- |
| `make check` | 通过：Ruff（含 C901/PLR0912/PLR0913 新规则）、Pyright 0 错误、快速测试 117 项、API 快照一致、提交策略配置、结构度量、Import Linter、deptry、Pylint 10.00/10 |
| 真实数据库集成 | `make test-integration` 3 项通过 |
| 真实 HTTP 系统测试 | `make test-system` 2 项通过 |
| 覆盖 | `make coverage` 128 项（快速+集成）通过；独立行覆盖 100%、独立分支覆盖 100%（原始计数分别核对）；综合 100% |
| 后端变异（全新缓存） | 删除 `mutants/` 后重新生成：27/27 杀死，0 幸存/未测/超时/中断/段错误；门槛读取 quality-policy 配置 |
| 安全 | pip-audit 0 漏洞 0 警告；Semgrep 4 规则扫 16 文件 0 命中；npm audit 0 漏洞（2 个 moderate 的 qs 传递依赖已用 `npm audit fix` 处理并复验） |
| fixture 评测 | 4/4 合成案例通过 |
| hooks | 真实时钟 check-now 通过（20:0x，窗口外）；commit-msg 用真实消息文件验证正反例；ruff/pyright hook 用显式文件验证通过。仓库初始 commit 已由文档会话在合法时段创建后，文件类 hook 将随已跟踪文件自动生效 |
| 前端 `make frontend-check` | format:check、ESLint、tsc strict（含 tests/configs）、API 类型漂移检查、dependency-cruiser 24 模块 0 违规、Knip 0 命中、Vitest 41 项通过，覆盖率 lines/branches/functions/statements 全部 100%（含未导入文件计入分母的实证：临时 probe.ts 以 0% 拉低总分后移除） |
| 前端变异 | Stryker 90 个变异全部杀死（100%），0 幸存/超时/未覆盖/编译错误；原始状态门槛脚本同过 |
| 前端 E2E | Playwright 4 项通过：增补平面字符 𠀀 端到端定位与高亮（真实 FastAPI + Vite + 代理）、版本不符可读错误、axe serious/critical 0、键盘可达；失败产物（trace/截图）配置保留 |
| 属性测试 | Hypothesis `evidhist-local`/`evidhist-ci`/`extended(1000)` profile 均实跑通过；fast-check 中断插件启用 failOnInterrupt |
| 提交策略矩阵 | 交接清单第 4 节矩阵逐行核对：现有用例覆盖全部行；新增“未维护年份 21:00 允许但仍提示维护年度日历”（`CommitDecision.hint` + CLI stderr 提示）为测试先行（红→绿）；CLI 退出码/revision 范围（首推/PR/普通推送/无效 revision 失败）用受控 FakeGit 验证 |
| API 契约漂移 | 受控漂移负例：隔离目录中改动快照 → `--check` 退出 1；缺失快照 → 退出 1；当前快照 → 退出 0 |
| 干净重装 | `uv sync --frozen`（含 mutation/security 组）与 `npm ci` 均按锁文件复装成功 |

本记录未覆盖：远程 CI 执行（仓库未发布）、`uv sync` 于全新机器的端到端安装（仅本机复装验证）、真实模型质量（未接入模型，fixture 只验证评分链路）、~~`diff-cover`~~（2026-10-18 已接入：见下节）、actionlint（按交接清单时机“发布 CI 前”顺延）、oasdiff/Gitleaks（按既定接入时机顺延）。无障碍人工核查（键盘全流程/屏幕阅读器实测）经用户 2026-10-09 明确：当前暂无无障碍需求，顺延至明确指示后再做；已实现的 axe 自动检查与键盘可达性 E2E 用例继续保留运行。仓库本轮未创建 commit（用户未要求）。

## 首版研究闭环：材料导入与运行入口（2026-10-18）

对应[首版最小技术方案](minimal-technical-plan-2026-10-18.md)与[试点材料清单](research/ming-pilot-materials-2026-10-18.md)。实现文件在 `src/evidhist/research/`，产物与运行记录不进版本库（`runs/` 已 gitignore）。

### 环境前提（本机实测）

- 工具链：Linux 版 uv 0.12.24 与 CPython 3.14.8 装在 `.toolchain/`（原 macOS 二进制保留为 `uv-0.12.24-macos-arm64`）；`uv sync --frozen` 重建 `.venv`。
- 数据库：本机 `sudo` 不可用，**未用 `make db-up`（docker）**；改为 conda-forge 的 PostgreSQL 18.6 + pgvector 0.8.6（`.toolchain/postgres`），数据目录 `.cache/pgdata`（测试库 55432）与 `.cache/pgdata-demo`（演示库 55433），以受管后台任务运行：
  `.toolchain/postgres/bin/postgres -D .cache/pgdata -p 55432 -k .cache/pgsock -c listen_addresses=127.0.0.1`
- 迁移：`make migrate`（测试库）与 `make demo-migrate`（演示库）。

### 用法

```bash
# 1) 导入试点 25 卷（幂等；原文散列必须与采集台账一致）
make import-ming                       # 或 scripts/import_ming_pilot.py --database-url …
# 2) 跑一次研究闭环（fake 执行器可离线验证全链路）
QUESTION='于謙在北京保衛戰中的作用是什麼?' EXECUTOR=pi REVIEWER=pi make research-run
# 3) 查看产物
ls runs/<run_id>/                       # report.md citations.json run.json review.json [pi_outputs.json]
```

### Pi／模型接入（参考 ForgeLoop 配置）

- 模型来自 `~/.pi/agent/models.json`（provider `cc-switch-open-code-go`、模型 `deepseek-v4.1-flash`）；PI 需要可写 HOME，故用 `.cache/pi-home` 作隔离 HOME（内含 `~/.pi` 配置副本）。
- **PI 本体零工具**：以 `--no-tools --no-mcp --no-extensions --no-skills --no-context-files --thinking minimal` 启动；材料访问全部由适配器代理 4 个只读工具（`list_materials/search/read/exact_quote`），工具调用计入运行预算。
- 三次调用：检索计划 → 论断与逐字引文 → 反证归纳；评审再单独调用一次（只看报告）。

### 试点运行记录（2026-10-18 实际执行）

| 运行 | 结果 |
| --- | --- |
| `pilot-20261018c` | 3 条论断通过程序校验；评审 **fail**——引文只有「于謙」「京師」等检索词，支撑不了论断（真实缺陷） |
| `pilot-20261018g` | 模型拒答（检索片段相关性不足），0 条论断；评审 insufficient |
| `pilot-20261018h` | 3 条论断通过程序校验、4 条证据落库；评审 **pass**（评语仍提示标题分层与状态措辞） |
| `pilot-final` | 3 条论断通过程序校验、3 条证据落库；评审 **fail**——引文支撑不了「上疏辯駁羅通」等表述（越界） |

`pilot-final` 用量：3 次研究调用 + 1 次评审，input 9,044 / output 13,910 tokens，工具调用 58/60。评审通过与否取决于模型采样与证据质量，**评审是验收输入之一，不代替用户复核**。

### 已知限制（未做）

- 论断越界仍会发生：程序校验只证明文字位置，防止越界依赖评审与用户复核；尚未加"论断必须复述引文"的硬约束。
- 反证仅记录检索词与命中数，未逐条列出反证内容（评审已两次指出）。
- 检索为纯子串匹配（无分词/排序服务），片段相关性靠"覆盖检索词数"排序。
- 未做跨来源互校、OCR 校对与材料入库外的自动化；失败后人工重跑（B05）。

## 2026-10-18 安全门槛替换与 CI 首跑修复

仓库首次推送到 GitHub 后 CI 第一次真实运行，暴露四类问题，本轮一并处理：

| 问题 | 处理 |
| --- | --- |
| `security` 作业失败：pip-audit 报 `mcp 1.29.0`（CVE-2026-59951），`mcp` 由 semgrep 引入 | 按用户要求把 semgrep 换成 bandit：`security` 组改为 `bandit>=1.8,<2` + `pip-audit`；删除 `.semgrep.yml` 与 `scripts/run_semgrep.py`，新增 `scripts/run_bandit.py`；`make sast` 目标名不变 |
| bandit 默认规则在工程脚本上产出 16 条 subprocess 形态告警（B404/B603/B607） | 在 `[tool.bandit]` 显式豁免并写明理由：脚本按字面量参数调用项目工具，不接受外部输入；真正危险形态（`shell=True`、`eval/exec`、`pickle`、关闭 TLS 校验）仍在拦截范围内 |
| bandit 报 `db_migrations.py` B608（表名拼接） | SQL 提为模块常量，并在被报告的两行加 `# nosec B608` 及理由；值一律走绑定参数 |
| bandit 报我新写的 `pi_rpc.py` B101（`assert`） | 改用 `cast` 表达“管道由 `create_subprocess_exec` 构造保证”，断言在 `-O` 下会消失，换成类型断言更严谨 |

CI 侧同时修复：

- `frontend-e2e` 作业原先没有声明 PostgreSQL service，Web 服务连 55432 被拒；现复用 `quality` 作业的 `pgvector/pgvector:pg18` 服务定义。
- `frontend-quality` 与 `quality` 作业卡在既有的 ESLint `max-lines-per-function`：`SourceForm.tsx` 的 `SourceForm` 有 56 行。把 `.txt` 读取逻辑抽到 `frontend/src/components/sources/importText.ts`（含 4 条单元测试），组件降到 50 行；同时补了非 UTF-8 与读取失败两条组件测试。

本地验证：`make check` 退出码 0（174 项）；`make security` 退出码 0（pip-audit 无已知漏洞、bandit 0 命中）；`make frontend-check` 退出码 0（101 项测试，覆盖率 97% 行 / 91% 分支）。

### 覆盖与增量门槛（2026-10-18 补齐）

CI 质量作业还暴露两处与本轮改动相关的问题，已一并处理：

| 问题 | 处理 |
| --- | --- |
| 集成测试依赖 `crawler/data-ming/`（不随代码发布，CI 无此目录） | 语料改为可生成：`scripts/import_ming_pilot.py` 新增 `--data-dir`，集成测试在本地用真实 25 卷、在无该目录时按同样结构生成 25 卷合成语料（同样的 sha256 登记、许可与卷次），断言不变；`EVIDHIST_MING_CORPUS=synthetic` 可强制走合成分支 |
| Git 基线出现后增量覆盖门槛卡在 `pending_integration` | 按交接清单接入 `diff-cover`（dev 组）：`scripts/check_coverage_thresholds.py` 用 `reports/coverage.xml` 对基线比较，测量不到可测行（仅测试/文档改动）标“不适用”，diff-cover 未产出报告则判失败；基线等于 HEAD 时（直推 main）回退到 `HEAD~1`，避免门槛空转 |
| 分支覆盖 82% 低于 90% | 补 `review.py` 契约测试（14 例：判定、字段、缺评、超时、协议错误）与检索/解析不变量测试（20 例：检索词拆分、片段窗口与归并、论断与引文窄化、RPC 容错解析），分支覆盖升至 94% |

实测：`make coverage` 退出码 0（行 98.9%、分支 93.8%、改动行 100%）；`make check` 219 项通过。

## 对话功能（2026-10-19 起为界面主入口）

设计与决策见[对话功能技术方案](chat-feature-plan-2026-10-18.md)。要点：

- **启动**：`make demo-run`（后端 127.0.0.1:8000，指向演示库）+ `make frontend-run`（前端 127.0.0.1:5173）。界面只保留对话；材料与论断由对话内的工具读写，不再有独立页面入口。
- **PI 配置（环境变量）**：`EVIDHIST_PI_PROVIDER`（默认 `cc-switch-open-code-go`）、`EVIDHIST_PI_MODEL`（默认 `deepseek-v4.1-flash`）、`EVIDHIST_PI_HOME`、`EVIDHIST_PI_BIN_DIR`、`EVIDHIST_PI_COMMAND`（测试指向假 PI）、`EVIDHIST_CHAT_WALL_SECONDS`（每轮墙钟上限，默认 300）、`EVIDHIST_CHAT_REVIEW=0` 关闭评审。
- **工具**（宿主代理执行，PI 本体零工具）：`list_materials`／`search`／`read`／`verify_citation`（程序硬校验）／`search_papers`（OpenAlex＋Crossref 题录，单源失败如实记录）／`import_paper_record`（题录入库，DOI/URL 幂等，仅题录字段）。
- **接口**：`POST/GET /v1/conversations`、`GET /v1/conversations/{id}`、`POST /v1/conversations/{id}/messages`（SSE）、`POST /v1/messages/{id}/stop`（幂等）。事件先落库（`message_events`）再推送，刷新后可重建；`token` 为 PI 的真实 `text_delta` 增量。
- **验证**：`make check`、`make coverage`、`make frontend-check`；`npm run e2e` 含对话用例（e2e 后端固定使用 `tests/fixtures/fake_pi.py`，不调用真实模型）。
- **已知限制**：引文以只读卡片呈现（无正文内联标记）；界面未提供「深度思考／智能搜索」开关（需要后端按轮次选项支持）；工作台视图（材料／论断／引文定位工具）代码与测试保留但无界面入口。
- **显示规则**：回答里不出现内部标识（version_id/UUID）与码点区间，出处写「材料·卷次」并附逐字原文。旧会话的正文由前端 `answerText.cleanAnswerText` 渲染前隐去标识与区间，并以「已隐藏 N 处…」说明；旧事件的引文缺材料/卷次时，后端在 `GET /v1/conversations/{id}` 读取时补齐。
