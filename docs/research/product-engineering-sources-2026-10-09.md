# 产品工程补充依据

核验日期：2026-10-09。事实来自作者原文、规范、官方文档或维护者元数据；项目选择明确标为建议。未进行安装兼容性或性能实测。

## 工程原则的出处

- **TDD 三法则**：先出现失败测试，再增加生产代码；测试增量以产生失败为限；实现增量以使当前失败通过为限。Robert C. Martin 同时说明更大尺度的红—绿—重构及架构边界审视。[The Cycles of TDD](https://blog.cleancoder.com/uncle-bob/2014/12/17/TheCyclesOfTDD.html)
- **依赖规则**：源码依赖指向内部策略层；业务规则不应依赖外部数据库、界面或框架的数据结构。四层图是示意，不要求固定四层。[The Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- **SOLID**：SRP 按变化原因组织模块；OCP 支持扩展；LSP 保持可替换行为；ISP 减少不必要接口依赖；DIP 依赖抽象。不能把“每类只允许一个方法”当作单一职责原则。[Solid Relevance](https://blog.cleancoder.com/uncle-bob/2020/10/18/Solid-Relevance.html)
- **测试金字塔**：Mike Cohn 原文讨论单位、服务和界面层测试的组合，强调常被遗漏的服务层；不存在这里可引用的固定测试数量比例。[Cohn 原文](https://www.mountaingoatsoftware.com/agile/the-forgotten-layer-of-the-test-automation-pyramid)
- **mutmut** 是 Anders Hovmöller 维护的 Python 变异测试工具，不是 Robert C. Martin 提出的工具。[维护者与项目说明](https://pypi.org/project/mutmut/)

建议：上述原则落实为业务规则可独立测试、外部资源通过适配器接入、持续重构与行为测试；测试覆盖率和变异分数是项目自定验收指标。

## Python 生命周期与工具兼容性

| 分支 | 本次官方页面状态 | 支持结束 |
| --- | --- | --- |
| 3.12 | 仅安全维护 | 2028-10 |
| 3.13 | 仅安全维护 | 2029-10 |
| 3.14 | 缺陷修复阶段 | 2030-10 |
| 3.15 | 仍标记预发布 | 预计 2031-10 |

来源：[生命周期](https://devguide.python.org/versions/)、[下载页](https://www.python.org/downloads/)。3.15 的生命周期表仍显示原计划 10-01；更新于 10-02 的 [PEP 790](https://peps.python.org/pep-0790/) 把正式版列为预计 2026-10-09。本次抓取未确认正式发布，不能把计划日期当成已发生事实。

建议：以标准 Python 3.14 为主线。mutmut 和 [Semgrep](https://pypi.org/project/semgrep/) 当前包分类均列出 3.14，但这只是维护者声明；仍须对锁定版本在 macOS/Linux 实跑。mutmut 需要 fork，Windows 使用 WSL，且依赖 libcst 的可用轮子；自由线程构建另行验收。[mutmut 平台要求](https://mutmut.readthedocs.io/en/latest/)

## 前端工具的分工与运行条件

| 工具 | 官方用途与核验边界 |
| --- | --- |
| [TypeScript](https://www.typescriptlang.org/tsconfig/strict.html) | `strict` 开启一组静态类型检查；升级可能增加诊断。 |
| [ESLint](https://eslint.org/docs/latest/use/getting-started) | 可配置的代码规则；当前要求 Node `^20.19`、`^22.13` 或 `>=24`，配置采用 flat config。 |
| [Prettier](https://prettier.io/docs/install) | 格式化；官方建议项目本地精确锁定版本，CI 用 `prettier --check .`。 |
| [Vitest](https://vitest.dev/guide/) | 测试运行器；当前 guide 要求 Node `>=22.12`、Vite `>=6.4`；CI 用 `vitest run`。 |
| [Testing Library](https://testing-library.com/docs/react-testing-library/intro/) | 按用户可见 DOM 行为测试 React；需要 DOM 环境及相关 peer dependencies，本身不是运行器。 |
| [MSW](https://github.com/mswjs/msw) | 在浏览器/Node 拦截网络请求复用模拟处理器；不证明真实后端符合契约。 |
| [Playwright](https://playwright.dev/docs/intro) | 真实浏览器端到端测试；另装浏览器及系统依赖，当前列出 Node 22/24/26、macOS 14+ 等平台要求。 |
| [axe-core](https://github.com/dequelabs/axe-core) | 自动可访问性检查；无法判定项需人工复核，不能替代键盘与辅助技术检查。 |
| [fast-check](https://fast-check.dev/docs/introduction/) | JS/TS 性质测试，生成输入并缩减失败样例，接入已有运行器。 |
| [StrykerJS](https://stryker-mutator.io/docs/stryker-js/getting-started/) | 变异测试；[当前源码 engines](https://github.com/stryker-mutator/stryker-js/blob/master/packages/core/package.json) 要求 Node `>=22`；[Vitest 插件](https://stryker-mutator.io/docs/stryker-js/vitest-runner/) 须与所锁版本配套。 |

建议：React + TypeScript，Node 24 为共同基线；锁定具体包及 peer dependencies 后验收。组件测试验证加载、错误、空数据与争议状态，浏览器测试验证原文定位与图谱操作，Stryker 先覆盖领域计算。项目脚本调用本地工具，避免缺包时由 `npx` 隐式拉取新版本。

## GitHub 产品化、提交与许可

**事实**：[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) 定义 `type(scope): description`、`feat`/`fix` 与 `!`/`BREAKING CHANGE`；提交格式不是代码正确性的证明。[Git hooks](https://git-scm.com/docs/githooks) 明确 pre-commit 和 commit-msg 可通过 `--no-verify` 绕过。建议本地 hooks 提供快速反馈，GitHub CI 重跑完整门槛并结合仓库规则管理合入。

**事实**：[MIT](https://opensource.org/license/mit) 允许使用、修改、分发及销售，但须保留许可与版权声明；[Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) 另含明确的贡献者专利授权及相应终止、通知条款。[OSI 开源定义](https://opensource.org/osd) 不允许禁止商业领域使用，因此带 NC 限制的代码许可不满足该定义。Creative Commons 也建议软件使用专门的软件许可证；文档与独立素材可使用 CC。[CC 官方 FAQ](https://creativecommons.org/faq/#can-i-apply-a-creative-commons-license-to-software)

建议：代码采用 MIT 或 Apache-2.0，原创文档与数据分别标识授权范围；第三方史料保留原许可。当前 README 的 CC BY-NC-SA 与“OSI 意义上的开源软件”目标需要明确协调，不能仅因仓库公开就称许可问题已经解决。
