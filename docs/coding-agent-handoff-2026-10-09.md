# 代码 Agent 交接清单

日期：2026-10-09。用户已明确当前会话后续只修改文档，代码实现由其他 Agent 完成。本文是实现与验收任务说明，不代表下列代码工作已经完成。

## 1. 已确定的产品与工程要求

- EvidHist 是个人产品项目，代码计划在 GitHub 开源；围绕可使用、可维护的用户任务交付。
- 代码、配置、脚本、测试和代码示例采用 MIT；原创文档采用 CC BY-NC-SA 4.0；第三方材料保留原许可。
- Python 目标基线为标准 CPython 3.14.8，uv 固定为 0.12.24。前端方案为 React、TypeScript、Node 24。
- 使用 Uncle Bob 的 TDD 三法则、红—绿—重构、SOLID 和依赖规则；mutmut/Stryker 是对应测试工具，测试金字塔的来源另归引 Mike Cohn。
- 北京时间法定调休工作日 09:00（含）至 18:00（不含）禁止 commit，午间包含在禁止窗口内。
- 2026 年放假与补班按已引用官方通知维护；缺少年度日历时，该窗口内拒绝提交，窗口外可提交。
- 当前仓库没有初始 commit，现有文件均未提交；不得为了测试 hooks 在禁止时段创建真实 commit，也不得伪造时间。

详细方案见[架构文档](architecture-analysis-2026-10-09.md)，协作规则见[CONTRIBUTING](../CONTRIBUTING.md)。

## 2. 当前实现状态与已知问题

本轮前段已经产生部分代码、配置和测试草稿；用户明确仅维护文档后，主会话停止了代码修改，没有自动回退这些已有改动。以下状态已结合本次只读复核更新：`make check` 在 3.14.8 上通过，包括 76 项快速测试、API 快照和提交策略配置检查。该结果不覆盖数据库、系统、变异、安全及新增阈值方案的全部验收。

| 范围 | 已知状态 | 后续责任 |
| --- | --- | --- |
| Python 环境 | 3.14.8 下 `make check` 已通过，uv 0.12.24 已进入开发组 | 补齐其他新基线检查与发布安装验证 |
| 解释器位置 | 只读复核确认 `.venv` 基础解释器已指向项目 `.toolchain/python/cpython-3.14.8-macos-aarch64-none` | 验证干净安装，保留持久路径要求 |
| 提交规则 | `src/evidhist/commit_policy.py`、CLI、年度日历、hooks、CI 与新增用例已提供，基础检查已通过 | 继续核查 hooks、CI revision 范围及真实使用边界 |
| 之前的类型错误 | 本次 Pyright 已无错误/警告，先前审计参数问题已不再阻断 `make check` | 保留 CLI 错误/异常契约验证 |
| 网络限制 | 之前的重建尝试受沙箱网络限制；当前持久路径已可见 | 新增工具安装按环境机制处理，不能因下载失败跳过检查 |
| API 契约 | 当前快照一致性检查已通过 | 继续验证故意漂移时的失败及 API 兼容性 |
| 前端 | 设计方案完整，尚无业务界面、npm 锁文件及浏览器执行结果 | 按第 16 章实现前端工程基础及首个真实界面 |
| 验证历史 | 3.12 旧骨架的 40 项测试、100% 源码覆盖、27 个变异曾通过；3.14.7 预检的原有 35 项快速测试通过 | 两者均不能代替 3.14.8 和新增实现的完整验收 |

临时 PostgreSQL 测试容器已清理。重新验证时只使用项目专用测试数据库与带标签资源，不操作无关容器。

## 3. Python 与后端工程的完成条件

保持目前已通过的类型检查和持久解释器绑定，确认版本声明、实际运行时、锁文件、Ruff、Pyright 与 CI 一致。持久环境应可按开发说明重新安装，而不是依赖某次临时下载目录。

随后运行格式、Lint、类型、原有及新增单元/属性/组件/场景用例、真实 PostgreSQL/pgvector 集成与真实 HTTP 系统测试。覆盖门槛和变异门槛沿用已确定范围，失败、跳过和超时分别报告。

在 3.14.8 上执行 mutmut、pip-audit、Semgrep 和 fixture 评分器，确认原生依赖、fork、证书、缓存与路径兼容；不得只依据安装成功或分类器声明判断兼容。原有测试和锁文件都是需要复核的输入。

API 契约检查既验证当前一致，也用受控临时变更验证能够发现漂移。真实模型没有接入时，不报告模型准确率或费用；fixture 仅验证评分链路。

## 4. 提交策略的验收矩阵

公共边界为时间判断、提交消息判断、CLI 退出码、hooks 调用与 CI revision 审计。

| 场景 | 预期 |
| --- | --- |
| 2026-10-09 08:59:59 北京时间 | 允许 |
| 2026-10-09 09:00:00、17:59:59 | 拒绝 |
| 2026-10-09 18:00:00 | 允许 |
| 2026-10-10 周六 12:00，官方补班 | 拒绝 |
| 2026-10-11 周日 12:00，普通休息日 | 允许 |
| 2026-10-01 周四 12:00，官方放假 | 允许 |
| 同一瞬间用 UTC 表达 | 转换后得到相同判断 |
| 无时区时间戳 | 明确失败，不默认机器本地时区 |
| 未维护年份的 12:00 | 拒绝，不默认周末放行 |
| 未维护年份的 21:00 | 允许，仍提示应维护年度日历 |
| 相互冲突或错误年份的日历 | 配置失败 |
| 合规 Conventional Commit 首行 | 通过消息校验 |
| 空描述、未知 type、非法 scope、超长首行 | 拒绝 |
| 作者时间或提交者时间位于禁止窗口 | CI 拒绝该新增 commit |
| CI 在禁止窗口运行，但 commit 时间合规 | 不因 CI 运行时间拒绝 |

检查提交开始与消息阶段的真实时钟，减少跨越禁止起点的检查间隔。CI 对初次推送、PR、普通推送和手动运行选择正确 revision 范围；无效 revision 或无法审计不能被报告为通过。

可通过注入明确时间、消息 fixture 及受控日志验证逻辑。验证过程中也遵守时间限制；不得修改系统时钟或伪造 Git 时间字段。Git hooks 和 Git 时间戳不能保证不可绕过，公共仓库仍须必要状态检查、分支保护与维护者审阅。

## 5. 前端工程任务与完成条件

实现前先锁定 Node 24 下实际兼容的工具版本与 peer dependencies，创建可复现 npm 锁文件。接入 TypeScript strict、ESLint flat config、Prettier、Vitest、Testing Library、user-event、MSW、fast-check、Stryker/Vitest runner、Playwright 和 axe 的对应入口。

基于后端 OpenAPI 快照生成类型，使用运行时 Schema 验证回应，真实 API 契约用例补充 MSW。验证扩展汉字和 UTF-16/code point 转换，避免引文高亮错位。

首个真实界面应围绕已有引用定位接口完成输入、提交、结果、失败与原文高亮。界面必须说明其校验的是显式提供文本中的位置与字句，不能把位置匹配展示为来源真实性或史实已经证实。

组件用例覆盖加载、非法响应、空结果、网络失败、取消与旧响应；属性用例覆盖区间与 Unicode；Stryker 先覆盖这些领域规则。Playwright 至少验证一次真实前后端完整流程及对应错误流程，保留失败产物。自动 axe 检查与键盘/焦点的人工检查分别记录。

提供可运行的本地脚本和 CI 作业；任何空测试、全部跳过、工具崩溃或缺少浏览器都不能算作 UI 验收通过。前端服务启动、构建基础路径和 API 地址同时验收。

## 6. 工程方法与产品交付

以实际公共行为写失败样例、小步实现，再在测试保护下改善结构。按变化原因和外部边界组织模块，避免为了形式构建大量抽象层。维护者审阅测试是否忠实表达了用户任务，是否能捕获反例。

核心规则的通过条件包括明确示例、属性边界与有效变异结果。覆盖率用于定位遗漏，不替代语义；模型、工具或依赖自报成功不替代独立验证。

发布记录实际执行环境、材料/配置版本、适用检查和未完成项。代码与文档许可声明保持一致，第三方材料来源独立标识。GitHub 仓库创建或发布仍依据用户在相应任务中的请求执行。

## 7. 完成后需要交回的证据

- 实际 Python/uv/Node、系统与浏览器版本；可重复安装步骤。
- 新基线各层测试结果、覆盖范围、变异范围与全部状态、安全发现及处置。
- 提交策略配置来源、边界/异常/CI 范围案例与 hooks 验证方式。
- API 契约及前端生成物的漂移检查，真实前后端流程结果。
- 已完成能力、仍待实现能力、未运行检查及原因。
- 临时服务已清理，用户未要求的 commit 或远程发布未执行。

将实际结果补入开发文档，不覆盖旧环境的历史记录，也不在验收之前更新为“全部通过”。

## 8. 维护性检查值：来源、项目选择与执行级别

用户再次确认本会话仅修改文档。因此下列配置是**供代码 Agent 合并与验收的模板**，未写入实际检查配置，未安装新增工具。官方默认值提供起点，项目选择依据风险、维护成本和真实代码调整；没有证据证明存在适用于所有函数或产品的最优数字。

### 8.1 推荐的结构门槛

| 指标 | 官方默认或参考 | EvidHist 建议 | 执行方式 |
| --- | --- | --- | --- |
| 函数有效代码行 | ESLint 函数行数默认 50；Lizard 提供 NLOC | 40 行提示，超过 50 行失败 | Python 精确 AST/tokenize 门槛；前端 ESLint，加必要的口径校准 |
| 本类公开接口 | Pylint 公开方法默认 20 | 超过 10 提示，超过 20 失败 | 方法用 Pylint 辅助，属性/重载去重等完整口径由专用检查补足 |
| 手写源码文件总行数 | ESLint 默认 300；Pylint 默认 1000 | 超过 300 提示，通常上限 500；经审阅的单项例外上限 1000 | Python Pylint、前端 ESLint；例外单独记录，不全局放宽 |
| 圈复杂度 | Ruff/Pylint 默认 10；NIST 也讨论 10 的依据与例外 | 超过 10 失败 | Ruff `C901`；前端 ESLint `complexity` |
| 参数数量 | Ruff/Pylint 默认 5；ESLint 默认 3 | 超过 5 失败 | `PLR0913`、`max-params`；考虑 self/cls/this 的口径 |
| 分支数量 | Ruff/Pylint 默认 12 | 超过 12 失败 | Ruff `PLR0912` |
| 嵌套深度 | ESLint 默认 4 | 超过 4 失败 | 前端 `max-depth`；Python 专用度量或核验后的插件 |
| 返回语句数量 | Ruff/Pylint 默认 6，二者 return/yield 口径可能不同 | 超过 6 提示 | 初期作为审阅报告，不能为了少返回而增加嵌套 |
| 局部变量数量 | Pylint 默认 15 | 超过 15 提示 | 定向 Pylint 报告；避免以复杂表达式压缩变量数量 |
| 语句数量 | Ruff `PLR0915` 默认 50 | 超过 50 提示 | 补充指标，不能替代函数行数 |
| 单行长度 | 项目已有 Ruff 100 | 保留 100 | 与现有格式保持一致；前端 Prettier 同步打印宽度 |

保留函数 50 和公开接口 20，是因为它们与常用工具起点一致；文件 500 是新产品的项目折中值，**不是官方默认或实证最优值**。1000 保留为审阅后的绝对例外上限，而不是普通文件目标。先报告现有命中，再对新代码落实，避免机械切割有清楚职责的模块。

依据：[ESLint 函数行数](https://eslint.org/docs/latest/rules/max-lines-per-function)、[文件行数](https://eslint.org/docs/latest/rules/max-lines)、[参数](https://eslint.org/docs/latest/rules/max-params)、[嵌套](https://eslint.org/docs/latest/rules/max-depth)、[Pylint 选项](https://pylint.readthedocs.io/en/stable/user_guide/configuration/all-options.html)、[Ruff 设置](https://docs.astral.sh/ruff/settings/)、[Lizard](https://github.com/terryyin/lizard)。NIST SP 500-235 第 2.5 节支持复杂度 10 作为起点，同时明确具体上限及例外仍需论证；它不能证明 50/20/500 这组现代产品阈值最优。[NIST 原文](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication500-235.pdf)

### 8.2 必须固定的统计口径

- 函数行数从声明行到函数结束，包括多行签名；装饰器在范围外不计。排除空行、纯注释，以及 Python AST 识别出的真实 docstring；尾部注释所在行的代码仍计入。
- 字符串内的 `#`、多行 SQL/模板字符串仍是代码，不能正则删除后当注释排除。嵌套函数分别检查，其内容也保留在外层函数的范围中。
- 公开接口建议定义为本类声明的公开方法和公开 property；按“静态/实例接收者 + 名称”去重，getter/setter 和同一方法的 overload 合并。不计继承接口、构造器、Python 下划线私有/特殊方法、TS private/protected/#private；TS 单纯以下划线命名仍可能是 public。
- 普通数据字段不纳入方法/property 指标，其序列化契约另审阅。Pylint `R0904` 主要计数本类公开方法，不能把它直接宣称为上述全部接口口径。
- 文件门槛计算物理总行数，包含注释和空行，与函数有效行数不同。只对手写源码应用；Markdown、锁文件、原始史料、数据和可验证的生成物使用各自规则。
- 生成代码必须有可重复生成步骤和漂移检查。例外记录文件/函数、规则、理由、负责人、审阅和复核日期；不允许以折叠多条语句、删除必要说明或全目录忽略规避门槛。

代码 Agent 应以 50/51、20/21、500/501 的边界样例，加多行字符串、装饰器、属性、重载、嵌套、匿名/异步函数及 Python 3.14 语法验证计数。Lizard 的 NLOC 可辅助分析，但其解析器存在软性遗漏/误判边界，不能以“未识别到函数”视为严格门槛通过。

## 9. 测试与可靠性数值基线

| 指标 | 项目建议值 | 必须一起报告的条件 |
| --- | --- | --- |
| 后端行覆盖、分支覆盖 | 各 ≥90% | 两个独立原始计数；当前综合 90% 不能冒充两项各 90% |
| 新增/修改代码的行覆盖 | ≥90% | diff-cover；无有效 Git 基线或无可测量新增行时标“不适用” |
| 前端覆盖 | lines/branches/functions/statements 各 ≥90% | 明确源码 include；不能只测已导入文件 |
| 当前关键领域的变异 | 有效非等价变异全部捕获，无未解释幸存 | 维持原核心范围严格门槛，等价项逐条审阅 |
| 扩展的一般模块变异 | 非等价、有效变异的 killed 比例 ≥90% | 90 是项目试行值；总数必须 >0，超时不自动算有效捕获 |
| 变异异常/未完成 | 0 个未处置状态 | no coverage/no tests、timeout、pending、工具崩溃分别检查 |
| 属性样例数 | 本地 100，PR 高风险规则 300，发布前扩展 1000 | 是执行预算，不是统计置信度；保留 seed、最小反例及实际次数 |
| Python 单测试时限 | 初始 30 秒；特定系统场景可单项 60 秒 | 包含 fixture；超时为失败/未完成，核对资源清理 |
| Vitest 测试/钩子 | 5 秒 / 10 秒，重试 0 | 按实测调整，不能掩盖死锁或未等待 Promise |
| Playwright 测试/断言 | 30 秒 / 5 秒 | 沿用官方起点；导航 15 秒、动作 10 秒是项目预算 |
| UI 重试 | 本地 0，CI 最多 1 次诊断重试 | `failOnFlakyTests=true`；保留初次失败，不无条件算通过 |
| UI CI 总预算 | 初始 10 分钟，2 workers | 需要真实负载校准；超时不报告为完成 |
| CI 错误/非法配置/空关键测试 | 0 | 禁止 `test.only`，没有测试或报告缺失直接失败 |
| 新增依赖循环/越层依赖 | 0 | 区分运行时与纯类型依赖；不能靠遗漏入口达标 |
| 未处置密钥命中 | 0 | 单列误报与真实泄漏；脱敏报告、工作树与历史分别扫描 |
| 未批准的破坏性 API 变更 | 0 | OpenAPI 差异与客户端用例；版本化变更须解释迁移 |
| 可访问性 | 关键流程 serious/critical 未处置项 0 | moderate/minor/incomplete 仍需逐项处置，人工键盘检查另报 |

这是一套待校准的产品政策，除了已标注工具默认的项，其余数字都是项目建议。性能、费用、备份 RPO/RTO 和真实模型质量目前缺乏负载与标注依据，先测量再冻结门槛，不给出看似通用的数字。

一般模块的 killed 比例需明确分母：以有效、非等价变异中的 killed、survived、no coverage 及有效 timeout 总数为分母，timeout 不加入 killed。确认无效/等价项须有逐项理由并保留原始总数；pending 和未完成范围不能简单从分母删除后宣称完成。关键范围保留更严格的行为与变异验收。

coverage.py 开启分支后总百分比混合语句与分支，需从 JSON/XML 分别计算。Stryker 官方分数把 timeout 加入 detected，默认 `break=null` 不阻断低分；本项目必须增加原始状态核查。fast-check 限时中断也可能被当成成功，应匹配所锁版本的失败中断设置。[覆盖分母](https://coverage.readthedocs.io/en/latest/branch.html)、[Stryker 配置](https://stryker-mutator.io/docs/stryker-js/configuration/)、[Stryker 状态](https://stryker-mutator.io/docs/mutation-testing-elements/mutant-states-and-metrics/)、[属性/浏览器默认值核验](research/maintainability-tool-baselines-2026-10-09.md)

## 10. 可复制的检查配置模板

以下片段分别合并到对应文件，**不是新创建的配置文件，也不表示已通过工具验收**。不能重复定义现有 TOML 表、覆盖已有规则或在未安装插件时加入插件专用选项。代码 Agent 应锁定兼容版本、验证配置加载和正反例，再接入本地/CI。

### 10.1 项目统一策略草案：`config/quality-policy.toml`

这是供专用计数器/报告门槛读取的项目自定义格式，Ruff、Pylint 等不会自动识别它；需由代码 Agent 实现消费逻辑。

```toml
schema_version = 1

[scope]
handwritten_roots = ["src", "scripts", "tests", "frontend/src", "frontend/tests"]
extensions = [".py", ".ts", ".tsx", ".js", ".jsx"]
generated_roots = ["frontend/src/generated"]

[structure]
function_effective_lines_warn = 40
function_effective_lines_max = 50
exclude_blank_lines = true
exclude_comment_only_lines = true
exclude_python_docstrings = true
include_signature = true
include_nested_function_ranges = true
public_interfaces_warn = 10
public_interfaces_max = 20
public_interface_mode = "own-methods-and-properties"
file_physical_lines_warn = 300
file_physical_lines_max = 500
reviewed_file_exception_ceiling = 1000
reviewed_exceptions = []

[coverage]
line_min = 90
branch_min = 90
changed_line_min = 90

[mutation]
general_killed_min = 90
critical_unreviewed_survivors_max = 0
unresolved_incomplete_states_max = 0
require_nonempty_report = true

[property_tests]
local_examples = 100
ci_examples = 300
extended_examples = 1000
```

### 10.2 Python：定向扩充 `pyproject.toml`

保留现有 Ruff select/allowed-confusables 等，只合并以下新增规则与表。Pylint 初期只补 Ruff 未覆盖的公开方法和文件门槛，避免整套规则重复执行。

```toml
[tool.ruff.lint]
extend-select = ["C901", "PLR0912", "PLR0913"]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.pylint]
max-args = 5
max-branches = 12

[tool.pylint.main]
disable = ["all"]
enable = ["too-many-public-methods", "too-many-lines"]

[tool.pylint.design]
max-public-methods = 20

[tool.pylint.format]
max-module-lines = 500

[tool.coverage.run]
branch = true

[tool.coverage.report]
fail_under = 90

[tool.pytest.ini_options]
timeout = 30
timeout_method = "signal"
```

`timeout` 项需要 pytest-timeout；signal 方案仅用于项目支持的 Linux/macOS，仍需避免与被测代码的 SIGALRM 冲突。`fail_under` 保留现有综合门槛，**另外**从原始计数核对独立行/分支门槛。返回 6、语句 50 和局部变量 15 初期放入审阅报告，不直接在 blocking Ruff 中启用；执行错误不可用 `|| true` 隐藏。[pytest-timeout](https://github.com/pytest-dev/pytest-timeout)

参考命令（工具安装后）：

```sh
pylint --disable=all --enable=R0904,C0302 --max-public-methods=20 --max-module-lines=500 src scripts
coverage json -o reports/coverage.json
diff-cover reports/coverage.xml --compare-branch=origin/main --fail-under=90
```

diff-cover 的比较对象应在 PR 中替换为实际 base revision，初始仓库没有基线时不能直接执行上述示例并宣称增量覆盖通过。[diff-cover](https://github.com/Bachmann1234/diff_cover)

### 10.3 前端：TypeScript 与 ESLint

TypeScript 合并选项：

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitReturns": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true
  }
}
```

ESLint flat config 的 `rules` 内容示例；必须已有 TS parser、typescript-eslint 与类型信息配置，不能当作完整 ESLint 文件直接运行：

```json
{
  "max-lines-per-function": ["error", {"max": 50, "skipBlankLines": true, "skipComments": true, "IIFEs": true}],
  "max-lines": ["error", {"max": 500, "skipBlankLines": false, "skipComments": false}],
  "complexity": ["error", 10],
  "max-depth": ["error", 4],
  "max-params": ["error", 5],
  "max-statements": ["warn", 50],
  "@typescript-eslint/no-floating-promises": ["error", {"ignoreVoid": false}],
  "@typescript-eslint/no-misused-promises": "error"
}
```

Ruff 不提供逐规则 warning severity；ESLint 的 warning 也必须区分“报告提示”与“CI 把 warning 当 error”。当前 `max-statements` 是提示时，不应同时全局使用 `--max-warnings=0` 把提示变为硬门槛。遗漏 Promise 处理的规则可直接保护请求、取消与任务状态。[Promise 规则](https://typescript-eslint.io/rules/no-floating-promises/)、[误用 Promise](https://typescript-eslint.io/rules/no-misused-promises/)

### 10.4 前端：Vitest、Playwright、Stryker

`vitest.config.ts` 的合并起点；安装兼容的 jsdom 与 coverage provider，E2E 不进入 Vitest include：

```typescript
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{ts,tsx}', 'tests/unit/**/*.test.{ts,tsx}', 'tests/component/**/*.test.{ts,tsx}'],
    testTimeout: 5000,
    hookTimeout: 10000,
    retry: 0,
    passWithNoTests: false,
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.test.{ts,tsx}', 'src/generated/**'],
      reporter: ['text', 'json', 'lcov'],
      thresholds: { lines: 90, branches: 90, functions: 90, statements: 90 }
    }
  }
});
```

CI 使用 `vitest run --coverage`；include 需校准实际目录，避免未导入代码从分母消失。[Vitest coverage](https://vitest.dev/config/coverage)

`playwright.config.ts` 的起点，服务启动配置与真实 API 地址由代码 Agent 补齐：

```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  expect: { timeout: 5000 },
  globalTimeout: 600000,
  workers: process.env.CI ? 2 : undefined,
  retries: process.env.CI ? 1 : 0,
  forbidOnly: Boolean(process.env.CI),
  failOnFlakyTests: Boolean(process.env.CI),
  use: {
    actionTimeout: 10000,
    navigationTimeout: 15000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure'
  }
});
```

`failOnFlakyTests` 需要支持该选项的 Playwright（1.52+）。全局预算和 workers 是本项目建议，不是官方默认；在目标 CI 上实测后调整。[Playwright 配置](https://playwright.dev/docs/api/class-testconfig)

`stryker.config.json` 的一般模块起点：

```json
{
  "$schema": "./node_modules/@stryker-mutator/core/schema/stryker-schema.json",
  "testRunner": "vitest",
  "mutate": ["src/domain/**/*.ts", "!src/generated/**"],
  "reporters": ["clear-text", "json", "html"],
  "thresholds": {"high": 95, "low": 90, "break": 90},
  "timeoutMS": 5000,
  "timeoutFactor": 1.5,
  "concurrency": 2
}
```

还须读取 JSON 中原始状态：零变异、未测、pending、timeout、工具错误均不能被高分掩盖。关键引用/版本/状态规则适用第 9 节的更严格门槛，不会因为一般模块 `break=90` 自动放宽。等价及无效变异逐项解释。[Stryker 配置](https://stryker-mutator.io/docs/stryker-js/configuration/)

属性测试按 local/ci/extended 分别 100/300/1000 配置。Hypothesis CI profile 使用 `deadline=None` 避免慢机器单样例假失败，外层仍有测试/作业时限；fast-check 的有效次数不足或中断必须报未完成，按所锁版本设置失败中断并保留 seed/path。禁止用全局 suppress health check 掩盖生成器问题。

Hypothesis 可放入 `tests/conftest.py` 的 profile 注册模板（保留已有 fixture），再用 pytest 的 `--hypothesis-profile=evidhist-ci` 等参数明确选择：

```python
from hypothesis import settings

settings.register_profile(
    "evidhist-local", max_examples=100, deadline=200, derandomize=False
)
settings.register_profile(
    "evidhist-ci", max_examples=300, deadline=None, derandomize=True
)
settings.register_profile(
    "evidhist-extended", max_examples=1000, deadline=None, derandomize=False
)
```

fast-check 配置参数模板，传给真实业务性质用例的 `fc.assert`；这里没有定义或执行用例：

```typescript
const extended = process.env.EVIDHIST_PROPERTY_PROFILE === 'extended';
export const propertyParameters = {
  numRuns: extended ? 1000 : process.env.CI ? 300 : 100
};
```

PR 使用可复现运行，扩展检查使用变化 seed 并记录复现参数。若所锁 fast-check 支持限时中断插件，必须启用其 `failOnInterrupt`；若不支持，则采用明确的进程/作业外层时限并把中断报告为未完成，不能声称已经执行了目标次数。

## 11. 更多值得接入的工具与配置政策

| 工具 | 直接解决的问题 | 建议门槛 / 配置 | 接入时机 |
| --- | --- | --- | --- |
| Import Linter | Python 越层、领域耦合适配器 | 领域到 API/数据库的禁止依赖 0 | 先保护现有真实边界 |
| deptry | 未声明、传递依赖误用、依赖分组错误 | DEP001/003/004 未处置项 0；DEP002 逐包审阅 | Python 基础门槛修复后 |
| diff-cover | 新改代码被整体覆盖率掩盖 | 可测量新增行 ≥90% | 首次具备 Git base 后 |
| pytest-timeout | 死锁、无限等待、卡住的 fixture | 初始每测试 30 秒，单项系统例外 60 秒 | 验证 3.14 与信号兼容后 |
| actionlint | GitHub workflow 语法、表达式、运行命令错误 | 未处置错误 0 | 发布 CI 前 |
| oasdiff | OpenAPI 破坏性变化 | 未批准兼容破坏 0 | 已有稳定 API 基线后 |
| dependency-cruiser | 前端运行时循环、越层关系 | 新增循环和违反边界关系 0 | 首个前端工程建立时 |
| Knip | 未用文件、依赖与导出 | 已校准入口的未解释命中 0 | 路由、测试和生成入口已明确后 |
| Gitleaks | 工作树及历史中的密钥 | 未处置真实命中 0，报告脱敏 | 第一次 GitHub 发布前 |
| axe-core | 页面自动可访问性违规 | critical/serious 未处置 0；其余逐项处置 | 首个真实界面 |
| Radon/Xenon、认知复杂度 | 趋势或复杂函数定位 | 可先观察，避免与 Ruff 重复硬门槛 | 已有误报/缺陷基线后再选择 |

Gitleaks 当前维护者公告以安全补丁维护为主；应记录此选型边界。静态分析看不到所有动态导入、插件和库消费者，先校准入口和真实使用，不能批量删除命中项。[工具核验](research/maintainability-tool-baselines-2026-10-09.md)、[actionlint](https://github.com/rhysd/actionlint)、[oasdiff](https://github.com/oasdiff/oasdiff)

### 11.1 Python 导入边界和依赖声明

`pyproject.toml` 合并示例，当前域 DTO 使用 Pydantic，因此此例先禁止已明确不应依赖的 API/数据库层；Pydantic 值对象分离应按实际设计另处理：

```toml
[tool.importlinter]
root_package = "evidhist"
include_external_packages = true

[[tool.importlinter.contracts]]
name = "Domain must not depend on API or database adapters"
type = "forbidden"
source_modules = ["evidhist.domain"]
forbidden_modules = ["evidhist.api", "evidhist.database", "fastapi", "sqlalchemy"]
allow_indirect_imports = false

[tool.deptry]
extend_exclude = ["mutants", "\\.cache", "\\.toolchain"]
known_first_party = ["evidhist"]
```

参考入口为 `lint-imports` 和 `deptry .`。检查脚本的运行依赖也要声明；本项目 `scripts/` 下的检查脚本必须声明其运行依赖所属分组（例如 SAST 工具 bandit 属于 `security` 组），不依赖恰好安装的传递包；2026-10-18 起 semgrep 已由 bandit 替代。psycopg 驱动及 uvicorn 的字符串/CLI 用法若被报未用，例外应逐包解释并配启动证据，不能整个关闭 DEP002。[Import Linter](https://import-linter.readthedocs.io/en/stable/contract_types/forbidden/)、[deptry](https://deptry.com/usage/)

### 11.2 前端依赖边界

`frontend/.dependency-cruiser.cjs` 示例以在 frontend 目录执行为前提：

```javascript
module.exports = {
  forbidden: [
    { name: 'no-runtime-cycles', severity: 'error', from: {}, to: { circular: true } },
    {
      name: 'domain-does-not-import-ui-or-api',
      severity: 'error',
      from: { path: '^src/domain(/|$)' },
      to: { path: '^src/(components|pages|api)(/|$)' }
    }
  ],
  options: {
    tsPreCompilationDeps: false,
    tsConfig: { fileName: 'tsconfig.json' },
    doNotFollow: { path: 'node_modules' }
  }
};
```

此示例检查编译后运行时依赖；纯类型依赖另用报告观察，不能将两类混为同一循环门槛。前端真实目录、别名和入口变化时同步校准。[dependency-cruiser 选项](https://github.com/sverweij/dependency-cruiser/blob/main/doc/options-reference.md)

Knip 的校准起点（不是已有文件）：

```json
{
  "entry": ["src/main.tsx"],
  "project": ["src/**/*.{ts,tsx}"],
  "ignore": ["src/generated/**"]
}
```

结合 Vitest/Playwright 等插件加入真实测试与动态路由入口。没有现成 `src/main.tsx` 时，先创建真实应用入口，再运行工具；不能用不存在的入口得出无问题结论。生成物忽略须仍有契约漂移检查。[Knip](https://knip.dev/reference/configuration)

## 12. 配置落地与验收顺序

以第 2 节当前复核状态为起点，补齐 3.14.8 的其他适用门槛；再接结构度量、关键导入边界与依赖声明，随后接前端真实界面及其测试。各工具安装、版本锁定和配置加载分别验证，不一次性引入全部候选。

代码 Agent 对每个硬门槛至少提供一个可发现的负例：51 行、21 接口、501 文件行、复杂度 11、参数 6、错误架构依赖、低独立分支覆盖、空变异、超时、中断、未处理 Promise、重复 UI 重试、缺失报告及未维护日历。例外批准后单独验证范围，确保不会影响其他文件。

软提示和硬失败必须在机器报告中区分；工具解析/配置错误、未知版本选项及报告缺失属于失败。试运行记录误报、真实缺陷、耗时和豁免原因，以代表性代码调整政策。阈值修改与理由纳入同一 PR，不能依据某次失败临时降低数值使其变绿。

本节是检查配置的交接任务，不是实际配置或新的通过记录。完成后更新开发说明中的实际状态，同时保留旧环境验证历史。
