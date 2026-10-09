# 维护性与可靠性阈值：一手资料核验

核验日期：2026-10-09。本文只记录调研与建议，未安装工具、修改检查配置或执行新检查。已阅读项目开发、贡献与架构说明。下列“官方默认”是本次官方文档的值；`stable`、`latest` 和仓库主干可能继续变化，后续实施须核对锁定版本。

**没有得到适用于所有项目的最优阈值。** 工具默认值提供起点，不是缺陷率保证；本项目尚无比较不同阈值下误报、漏报与维护成本的实证数据。建议先记录基线，再根据真实缺陷与反馈成本调整，不能把团队偏好写成研究定论。

## 1. 复杂度与函数规模

| 指标 | Pylint 官方默认 | Ruff 对应默认 | EvidHist 建议起点 |
| --- | --- | --- | --- |
| McCabe 圈复杂度 | 10 | 10，`C901` | 新增业务函数以 10 为审阅线 |
| 参数数量 | 5 | 5，`PLR0913` | 超过 5 审查是否存在稳定的参数对象 |
| 分支数量 | 12 | 12，`PLR0912` | 先沿用 12，关注规则是否承担多个职责 |
| 局部变量数量 | 15 | 15，`PLR0914` | 先报告，检查转换步骤是否混杂 |
| 返回语句数量 | 6 | 6，`PLR0911` | 作为审阅提示，允许清晰的提前返回 |

来源：[Pylint 参数](https://pylint.readthedocs.io/en/stable/user_guide/configuration/all-options.html)、[Ruff 设置](https://docs.astral.sh/ruff/settings/)。上述数字在启用对应规则后才起作用；设置阈值本身不等于启用检查。Pylint 当前文档对 returns 的描述包含 return/yield，Ruff 描述为 return statements；相同默认数字不保证两个实现统计完全相同。规则稳定性也须以所锁 Ruff 版本为准。

**项目建议**：优先扩充现有 Ruff 的必要规则；不要为了同一指标同时叠加 Pylint、Radon、Xenon。例外按函数记录业务理由，避免全文件忽略。长表驱动解析、协议适配器与短小核心规则可以采用不同审阅尺度。不要为了减少返回次数引入更深嵌套，也不要为了减少局部变量把可读步骤压成复杂表达式。审阅线是否升级为硬门槛，应经过真实代码样本核验。

## 2. 覆盖率必须明确分母

**官方事实**：coverage.py 启用分支测量后，普通报告的总百分比同时计入语句与分支执行机会；XML/JSON 报告保留可区分的语句、分支信息。排除一侧分支也会改变测量分母。[coverage.py 分支覆盖](https://coverage.readthedocs.io/en/latest/branch.html)

**项目建议**：当前文档的“综合覆盖 90%”不能解释成“行覆盖和分支覆盖各 90%”。如果未来需要独立约束，建议分别统计行覆盖 ≥90%、分支覆盖 ≥90%，并单列引用定位、版本绑定、未知状态等核心模块；这属于待实施的新政策建议。零分支记为不适用，不能靠除零转换为通过。记录未导入模块和排除项，验证新增代码的遗漏路径。

可用 pytest-cov 收集分支，再导出 coverage JSON；阈值比较应基于原始计数，避免显示精度四舍五入影响边界。命令示例不是执行记录：

```sh
python -m pytest --cov=evidhist --cov-branch --cov-report=term-missing
python -m coverage json -o reports/coverage.json
```

达到覆盖率只说明相应路径被执行；错误的断言、错误的期望或来源不真实，仍可能全部通过。核心规则需要反例、性质测试和变异检查共同核查。

## 3. 属性测试的次数与时间预算

| 工具 | 官方默认 | 需要保留的边界 |
| --- | --- | --- |
| Hypothesis | `max_examples=100`；普通 profile 的 `deadline=200ms` | 例数不是函数调用次数；筛选、失败缩减等会改变实际执行量 |
| Hypothesis 当前内置 CI profile | `deadline=None`、`derandomize=True` | 与普通环境不同；应显式记录采用的 profile |
| fast-check | `numRuns=100`；单次 `timeout` 默认关闭 | 运行器自身仍可有超时；同步死循环不能靠普通 Promise 超时中止 |

来源：[Hypothesis 设置](https://hypothesis.readthedocs.io/en/latest/reference/api.html)、[fast-check 参数](https://fast-check.dev/docs/api/interfaces/Parameters/)。fast-check 的限时中断默认可能在未达到目标次数时报告成功；当前 API 文档把旧中断选项标为弃用，建议使用插件的 `failOnInterrupt: true`。升级前必须匹配所锁版本。

**项目建议**：普通性质测试先用 100 个有效样例；高风险规则的 PR 检查可试行 300，定期扩大到 1000，依据耗时和新增反例调整。这些是成本预算，不是统计置信度。异体字、空引文、重复片段、跨行定位、时间区间边界应由策略显式生成，不能仅增加次数期待随机碰到。固定种子用于复现，另保留变化种子的探索运行与最小反例。CPU 纯函数和联网测试分开；CI deadline 关闭时仍设置作业总时限，执行中断保留失败或未完成状态。

## 4. 变异测试的分数与异常状态

**官方默认**：Stryker 当前配置为 `high=80`、`low=60`、`break=null`；高低阈值影响报告颜色，`break` 才决定低分是否使构建失败。超时预算默认使用 `netTime × 1.5 + 5000ms + overhead`。[Stryker 配置](https://stryker-mutator.io/docs/stryker-js/configuration/)

**官方计分**：`detected = killed + timeout`，`valid = detected + survived + no coverage`，总分为 `detected / valid`。编译错误、运行错误不进入有效变异分母，ignored 与 pending 另列。因此分数 100% 也不能证明没有异常或未执行变异。[Stryker 状态与指标](https://stryker-mutator.io/docs/mutation-testing-elements/mutant-states-and-metrics/)

**项目建议**：保持当前限定核心范围的严格验收；主交接文档为一般模块选择 killed 比例 90% 的试行门槛，这是项目选择，不能把官方报告颜色的 80% 默认值当作产品验收标准。同步报告有效变异总数、幸存、未覆盖、超时和工具异常。零变异不得通过。等价变异逐项审阅并记录，不因难以杀死就批量排除。不能直接把 Stryker 的 timeout 算 detected 规则套入现有 Python 变异门槛；超时先复核，两套统计口径要写明。

## 5. 浏览器测试、重试与可访问性

**官方默认**：Playwright Test 单测试 30 秒、expect 断言 5 秒；动作、导航与整次运行没有各自的默认额外时限，但仍受适用的测试时限约束。默认重试为 0，首次失败而重试成功会标记 flaky。[超时](https://playwright.dev/docs/test-timeouts)、[重试](https://playwright.dev/docs/test-retries)

**项目建议**：沿用 30 秒/5 秒作为初始上限，依据本地服务和 CI 的实际分布调整；导航、长任务和作业设置明确预算。CI 最多增加一次诊断重试，保留第一次失败的 trace，flaky 单列处理，不能归入无条件通过。避免以固定 sleep 替代状态等待。

**官方事实**：axe-core 提供自动可访问性规则，并返回需要人工核查的不确定项；自动扫描覆盖不了所有问题。[axe-core](https://github.com/dequelabs/axe-core)

**项目建议**：研究主流程先要求无未处理的严重自动化违规，并逐项处置其余发现。键盘焦点、图谱替代文本、对照阅读顺序及色彩以外的争议提示另做人工验收。规则集、页面状态和扫描范围一起记录，不能将一次首页扫描称为全站可访问性通过。

## 6. 比数字更直接的维护性约束

| 工具与一手来源 | 能验证什么 | 本项目建议与限制 |
| --- | --- | --- |
| [Import Linter](https://import-linter.readthedocs.io/en/stable/contract_types/forbidden/) | 静态导入的禁用边界，含间接依赖；可纳入外部包 | 先保护领域层不得导入 FastAPI/数据库适配器；动态加载不等于已覆盖 |
| [dependency-cruiser](https://github.com/sverweij/dependency-cruiser/blob/main/doc/rules-reference.md) | JS/TS 循环、路径间依赖规则 | 对新增运行时循环及越层依赖设零容忍；类型导入与合法同层关系需明确建模 |
| [Knip](https://knip.dev/reference/configuration) | 未用文件、依赖及 exports，依赖入口与插件配置 | 先校准入口；默认不报告入口文件的未用 exports；发布库的外部消费者不可见 |
| [deptry](https://deptry.com/usage/) | 缺失、未用、直接使用传递依赖、业务依赖错放开发组 | 在项目环境运行；命令行启动包、插件发现和包名/模块名映射需要逐项说明 |
| [Gitleaks](https://github.com/gitleaks/gitleaks) | Git 历史、目录和标准输入中的密钥模式 | 分别覆盖工作树与历史并脱敏报告；零发现不是不存在泄漏的证明 |

Gitleaks 当前主干 README 声明功能已完成，后续以安全补丁为主；这是维护者公告，不代表已经验证某个未来替代工具。主干文档也不能替代锁定发布版验收。

**项目建议**：先引入能约束现有真实边界的检查，后考虑复杂度或未用代码报告。试运行两到四周，记录新增缺陷命中、误报比例、执行耗时及每次豁免的原因；这个观察周期是项目安排，不是学术推荐值。硬门槛应可解释、可复现且由负责人维护，配置完成、实际运行与产品任务验收分别报告。
