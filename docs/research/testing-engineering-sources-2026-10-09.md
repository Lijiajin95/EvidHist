# Day 1 工程与测试工具核验

核验日期：2026-10-09。以下“事实”来自官方文档、官方源码或工具维护者发布的包元数据；“建议”面向 EvidHist。示例展示配置接口，安装版本须由项目锁文件固定，并以实际执行结果验收。

## 运行环境

**事实**：本次读取的当前包元数据最低 Python 要求如下；这不代表旧版本的要求，也不保证所有平台都有二进制轮子。

| 工具 | 最低 Python | 维护者发布元数据 |
| --- | --- | --- |
| Ruff | 3.7 | [PyPI](https://pypi.org/project/ruff/) |
| Pyright Python wrapper | 3.7 | [PyPI](https://pypi.org/project/pyright/) |
| pytest | 3.10 | [PyPI](https://pypi.org/project/pytest/) |
| pytest-cov | 3.9 | [PyPI](https://pypi.org/project/pytest-cov/) |
| Pydantic、Hypothesis | 3.10 | [Pydantic](https://pypi.org/project/pydantic/)、[Hypothesis](https://pypi.org/project/hypothesis/) |
| mutmut | 3.10 | [PyPI](https://pypi.org/project/mutmut/) |
| pip-audit、Semgrep、pre-commit | 3.10 | [pip-audit](https://pypi.org/project/pip-audit/)、[Semgrep](https://pypi.org/project/semgrep/)、[pre-commit](https://pypi.org/project/pre-commit/) |

**建议**：项目以 Python 3.12 为初始运行基线，Linux CI 与 macOS 开发分别验收。Pyright 的 PyPI 包是社区维护 wrapper，不能称为微软发布的 Python 包；其运行还涉及 Node。`pythonVersion` 表示被检查代码的目标版本，应与项目运行基线一致。

## 静态检查与普通测试

**事实**：Ruff 在 `pyproject.toml` 中区分 `tool.ruff`、`tool.ruff.lint` 与 `tool.ruff.format`；Pyright 支持 `tool.pyright` 及严格检查。[Ruff 配置](https://docs.astral.sh/ruff/configuration/)、[Pyright 配置](https://github.com/microsoft/pyright/blob/main/docs/configuration.md)

```toml
[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]

[tool.pyright]
include = ["src", "tests"]
pythonVersion = "3.12"
typeCheckingMode = "strict"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers --strict-config"
```

**事实**：`tool.pytest.ini_options` 仍受支持；pytest 9 另提供原生 TOML 配置，两个格式不应混用。pytest-cov 提供分支覆盖与门槛参数，覆盖率配置可放入 coverage 配置表。[pytest 配置](https://docs.pytest.org/en/stable/reference/customize.html)、[pytest-cov 参数](https://pytest-cov.readthedocs.io/en/latest/config.html)

```sh
ruff check .
ruff format --check .
pyright
python -m pytest --cov=evidhist --cov-branch --cov-report=term-missing --cov-report=xml
```

**建议**：快速检查、真实数据库集成测试、变异测试和联网模型评测分开运行。覆盖门槛由项目规则显式设置，不以增加镜像实现的断言凑百分比；分母应包含未导入的业务模块，缺失测试不能解释为通过。

**建议**：工具版本约束与可重复安装是两项不同工作。直接依赖写入项目声明，传递依赖经解析后保存锁定结果；升级时重建干净环境，重新核验格式、类型、测试和审计。记录实际解释器与工具版本，避免开发机使用全局命令而 CI 使用另一套环境。模型、浏览器和数据库测试所需服务应有明确启动说明，缺失服务应报告未执行，不能自动降级成模拟测试后仍声称集成通过。

## 严格结构、性质与变异测试

**事实**：Pydantic 可在模型级启用 `ConfigDict(strict=True, extra="forbid")`；严格模式下 JSON 输入对日期等类型仍允许必要转换，因此 Python 对象入口与 JSON 入口不能假定行为完全相同。[严格模式](https://docs.pydantic.dev/latest/concepts/strict_mode/)、[模型配置](https://docs.pydantic.dev/latest/api/config/)

**建议**：显式测试非法枚举、额外字段、空证据定位、逆序时间区间和类型误传；schema 合法只表示结构可接受，不能证明来源真实或论断得到支持。

**事实**：Hypothesis 以 `@given` 和策略生成样例，`@example` 可保留回归输入；`derandomize=True` 的稳定性受 Python、Hypothesis 版本及测试函数变更影响。[Hypothesis API](https://hypothesis.readthedocs.io/en/latest/reference/api.html)

**建议**：测试去重幂等、文本定位保持、区间关系及聚合顺序无关等性质；保留失败样例，避免在常规性质测试中请求真实模型。

**事实**：当前 mutmut 3.8.0 发布页与文档使用 `source_paths`；需要 fork 支持，Windows 使用 WSL。macOS 默认禁用不安全的 setproctitle 调用。变异工作目录是 `mutants/`。[mutmut 文档](https://mutmut.readthedocs.io/en/latest/)

```toml
[tool.mutmut]
source_paths = ["src/evidhist/"]
pytest_add_cli_args_test_selection = ["tests/unit/"]
pytest_add_cli_args = ["-o", "addopts="]
```

```sh
mutmut run
mutmut browse
```

**建议**：先覆盖证据校验、区间和指标计算等纯逻辑；清空普通 pytest 的覆盖率 `addopts`，避免带门槛的覆盖插件干扰变异子进程。不要混入 mutmut 旧配置名或假定 Pyright 可作为其变异过滤器。幸存、等价、超时与未覆盖变异分别解释，运行完成不自动等于达到质量门槛。

## 依赖审计、SAST 与 hooks

**事实**：pip-audit 的 `--no-deps` 要求精确 pin；`--require-hashes` 还要求完整 hash。`--strict` 使依赖收集失败导致失败。审计针对已知依赖漏洞，并不证明包本身可信；`--locked` 支持的锁格式须核对，不能直接把任意工具锁文件交给它。[pip-audit 官方仓库](https://github.com/pypa/pip-audit)

```sh
# 完整的传递依赖已精确锁定并带 hash
pip-audit --strict --require-hashes -r requirements.lock.txt
# 已完整精确锁定、但没有 hash 的替代输入
pip-audit --strict --no-deps -r requirements.lock.txt
```

**事实**：Semgrep 可以本地 YAML 为规则输入；`scan` 默认发现问题仍可能返回 0，`--error` 使发现问题返回 1。2 表示执行失败，`--strict` 下语法错误返回 3，规则或配置错误另有非零码。[Semgrep CLI](https://docs.semgrep.dev/cli-reference)

```sh
semgrep scan --config .semgrep.yml --error --strict --metrics=off src/
```

**建议**：规则文件提交到仓库；CI 拦截所有非零状态并保留扫描报告，不能只拦截退出码 1。起步规则应针对明确不允许的动态执行、命令拼接等模式，单个规则命中为零不代表完成全面安全审计。

**建议**：联网审计的超时或漏洞数据库不可达属于执行失败，应保存原因并允许重试；不要包装成“零漏洞”。必须忽略的问题逐项登记漏洞编号、适用性依据、责任人与复查条件。静态扫描规则也应带最小正反样例，核对既能发现目标问题，又不会把允许写法全部拦截。

**事实**：hooks 的 stage 使用 `pre-commit`、`pre-push`、`manual`。pre-commit 4.4 起 `language: system` 改名为 `unsupported`，旧名称暂为兼容别名；该运行方式不自动建立工具环境。[pre-commit 配置](https://pre-commit.com/)

**建议**：使用 `repo: local` 调用已经锁定安装的工具；若锁定 4.4+，使用 `language: unsupported`。全项目命令配置 `pass_filenames: false`，需要每次执行时配 `always_run: true`。提交阶段只运行快速检查，慢测试放推送或手动阶段。先验证配置，再安装指定 hooks：

```sh
pre-commit validate-config
pre-commit install --hook-type pre-commit --hook-type pre-push
pre-commit run --all-files --hook-stage pre-commit
```

## UI 与模型评测

**事实**：Playwright Python 官方推荐 pytest 插件，浏览器需另行安装；当前文档要求 Python 3.8+，macOS 14+，并列出 Windows 11+/WSL 和受支持 Linux 发行版。[Playwright 安装与平台](https://playwright.dev/python/docs/intro)

```sh
python -m playwright install chromium
python -m pytest tests/e2e --browser chromium
```

**建议**：页面存在后测试原文回跳、冲突并列与未知状态。没有页面时保留测试契约和启动要求，不能拿空白页面冒充产品 UI 测试通过。

**事实**：LangSmith 的评测文档区分代码判定、人工评分与模型裁判；模型裁判评分仍需人工复核与校准。[评测方法](https://docs.langchain.com/langsmith/evaluation-concepts)

**建议**：Day 1 可落地版本化样例和确定性评分器，显式区分 fixtures、模型生成结果与人工 gold。模型接入后固定语料版本、模型标识、提示版本与量表，报告引用支撑、定位、冲突和未知状态；无真实模型调用时只声称评分器经过测试。带费用和网络波动的模型评测单独执行，按来源谱系切分数据，避免同源转引泄漏。
