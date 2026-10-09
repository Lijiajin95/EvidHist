# 开发与检查说明

设计与配置目标基线：**Python 3.14.8、uv 0.12.24**、Node（Pyright 使用；前端方案为 Node 24）、Docker（真实数据库测试使用）。项目定位为个人开源产品。首次执行需要下载锁定依赖与测试镜像；格式、单元、属性、组件和场景测试随后可离线运行。Python 支持范围与工具兼容性由 `pyproject.toml` 及 `uv.lock` 约束。

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

`make check` 还会检查 API 契约快照，修改接口后执行 `make api-schema` 并审阅兼容影响。前端工具选型、用户场景与 CI 门槛见[设计文档第 16 章](architecture-analysis-2026-10-09.md#16-前端产品工程可靠性方案)，目前尚无业务前端代码或浏览器执行结果。

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

覆盖门槛为 `src/evidhist` 的行/分支综合覆盖 90%。真实 HTTP 系统测试启动临时独立进程并在测试后关闭；API 组件测试使用受控数据库边界替身，两种结果分别报告。

## 变异与安全检查

```bash
make mutation
make security
```

mutmut 当前只修改引用定位领域文件，并以两个子进程执行。结果写入 `mutants/mutmut-cicd-stats.json`；门槛脚本拒绝零变异、幸存、未测、超时或未完成结果。调试使用 `.venv/bin/mutmut results`、`show` 或 `browse`。不要把自动生成的 mutant 应用到未保存的业务源码。

`make security` 审计完整锁定的运行和工程依赖，并执行本地 Semgrep 规则。漏洞查询需要网络；网络/工具失败意味着未完成检查。Semgrep 的规则、证书和日志入口在项目内管理，报告写入 `reports/`。当前四类规则覆盖危险命令执行、动态 Python 执行、不安全反序列化及关闭 TLS 校验的模式。

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

`.github/workflows/quality.yml` 定义质量、依赖/安全、变异和 commit 策略四个作业，锁定 Action SHA 与数据库镜像摘要。尚未发布远程仓库，因此没有远程 CI 执行证据；本地执行结果独立记录。

当前没有业务 UI 或真实模型连接，未生成 UI/实时模型通过结果。第一张研究界面进入实现时同时接入 Playwright 浏览器、关键交互案例和 CI；模型接入时提交真实预测与运行元数据。业务持久化的首次实现同时加入数据库迁移与升级验证。

详细方法论见[架构文档第 12、13 章](architecture-analysis-2026-10-09.md#12-测试方法论用不同层次验证不同承诺)。

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
| 前端 | 可靠性方案已确定；业务 UI、npm 锁文件、前端检查与浏览器测试待其他 Agent 实现 |
| 测试资源 | 本次专用临时数据库容器已清理 |

本会话后续工作限定为文档，代码任务、具体缺口及验收要求已移交到[交接清单](coding-agent-handoff-2026-10-09.md)。

## 待代码 Agent 接入的维护性门槛

新增方案及可复制配置见[交接清单第 8–12 节](coding-agent-handoff-2026-10-09.md#8-维护性检查值来源项目选择与执行级别)：函数 50 有效行、公开接口 20、普通手写文件 500 行（例外最多 1000）、复杂度 10、参数 5、独立覆盖和增量覆盖 90%，以及依赖边界、超时、变异原始状态和前端可靠性工具。

这些属于文档方案，尚未写入实际检查配置或产生新的通过记录。配置合并前确认现有基础入口，再验证工具版本、计数口径和每项门槛的负例，避免直接粘贴造成重复 TOML 表、缺插件或误判。

本次文档方案复核同时运行现有 `make check`：Python 3.14.8，76 项快速测试通过，Ruff/格式/Pyright、API 快照与提交策略配置检查通过。该结果只属于已接入检查，未证明上面的新增工具或阈值已经启用。
