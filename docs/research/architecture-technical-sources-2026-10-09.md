# EvidHist 架构技术依据核验

核验日期：2026-10-09。依据仓库 README 的设计目标及下列官方资料；项目尚未实现，本文没有性能测试结果。标为“事实”的内容来自资料，标为“建议”的内容是面向本项目的工程判断。链接用于解释能力与边界，不代表锁定安装版本。

## 1. Python 与 API 并发

**事实**：FastAPI 的异步并发适合等待网络、数据库等 I/O；CPU 密集任务需要另行安排并行执行。普通 `def` 路由和依赖由框架放入线程池，但在异步路由中直接调用的同步工具函数不会自动进入线程池。[FastAPI 并发说明](https://fastapi.tiangolo.com/async/)

**建议**：采用 Python 模块化单体，API 与后台 worker 独立进程。网络调用使用异步客户端、超时与并发限额；文本清洗、批量实体抽取、嵌入计算进入后台作业。根据实际计算库是否释放解释器锁以及 CPU/GPU 配置选择进程池或模型服务，不能把 `async def` 当作计算加速器。只有性能剖析证明局部瓶颈后，再考虑 Rust/C++ 扩展。

## 2. PostgreSQL、向量与中文检索

**事实**：pgvector 同时支持精确最近邻与近似索引。近似索引扫描后才应用过滤，可能不足目标结果数；迭代扫描可继续搜索，但受扫描预算限制。官方还列出过滤列索引、部分索引和分区方案。[pgvector 官方仓库](https://github.com/pgvector/pgvector#filtering)

**建议**：PostgreSQL 存储史料元数据、版本、论断、证据与任务状态；pgvector 作为检索通道。先以精确搜索建立召回基线，再按年代、语料集、文体等真实过滤组合评估 ANN。低相似度、空结果及不足 k 条是待解释的检索结果，不能直接解释为“没有历史证据”。

**事实**：PostgreSQL 全文检索解析器负责辨认词边界，内置一个通用解析器，其字符判断受 locale 影响；官方此页没有提供文言文分词质量保证。[PostgreSQL 文本解析器](https://www.postgresql.org/docs/current/textsearch-parsers.html)

**建议**：中文与文言文在应用层构造带版本的分词、字级 n-gram、异体字及别名索引；保存与原文的偏移映射。先验证术语、原句和人物别名的召回，再组合向量与重排。`ts_rank` 不应被描述为已经实现的 BM25；若采用 BM25，需明确具体实现并在相同语料上评测。检索表示可以归一化，原文及引文定位必须保留。

## 3. 图路径、历史时间与空间

**事实**：PostgreSQL 递归 CTE 可遍历关联结构，提供 `SEARCH` 排序与 `CYCLE` 环检测；排序表达并不等于对底层访问顺序的控制。[递归查询](https://www.postgresql.org/docs/current/queries-with.html)

**建议**：先用实体、关系断言及证据关联表构建图谱查询投影。AB 路径必须限制最大跳数、关系类型、有效时间、展开规模和超时；只在末尾 `LIMIT` 不能代替展开预算。每条边返回来源、争议和是否为推断，不能只展示裸连线。

**事实**：PostgreSQL 日期按公历计算，公历制定前也如此。[日期时间类型](https://www.postgresql.org/docs/current/datatype-datetime.html)

**建议**：把“事件发生时间”“史料成书时间”“采集/审核时间”分开。史料时间保留原记年、历法、精度、可能区间、换算依据及版本；不确定年份不能强制填成一月一日。年代区间和日级日期分别表达，不把年号、干支直接转换成 Unix 时间戳。历法换算算法及史学适用性仍需专项核验。

**事实**：PostGIS 提供 `geometry`、`geography`、坐标参考系及空间索引；地理类型的距离/面积可按椭球计算。其空间类型不会替项目建立历史地名沿革模型。[PostGIS 数据管理](https://postgis.net/docs/using_postgis_dbmanagement.html)

**建议**：需要空间查询时启用 PostGIS；地点实体另关联“某时段采用的名称/边界/坐标”，记录定位依据与误差范围。空间距离、同名或现代行政归属只能帮助生成候选，不能单独确认古代地点同一性。

## 4. SQLite、DuckDB 与专用图数据库

**事实**：SQLite 适合本地应用存储，但单个数据库文件同一时刻只有一个写入者。[SQLite 适用场景](https://sqlite.org/whentouse.html) DuckDB 普通嵌入式读写模式由一个进程访问文件，进程内可多线程写入；当前文档另列 Quack 与 DuckLake 协调的多进程方案，不能概括为永远不支持多进程写入。[DuckDB 并发](https://duckdb.org/docs/current/connect/concurrency)

**建议**：SQLite 用于单机原型、离线导出或本地缓存；DuckDB 用于评测快照、语料统计与批量分析。共享在线事务由 PostgreSQL 承担，避免原型阶段同时维护多个权威数据源。

**事实**：Neo4j 的 Cypher 可表达复杂路径与按跳数的最短路径；加权最短路径等算法可使用 GDS，图投影还涉及内存与构建代价。[Neo4j 路径说明](https://neo4j.com/docs/cypher-manual/current/patterns/shortest-paths/)

**建议**：图遍历成为核心负载，且关系库在代表性查询上的延迟或维护复杂度确实超标后，再引入图数据库。迁移对象优先是可重建的查询投影。最短路径表达连接方式，不自动证明因果、影响或证据强度。

## 5. 采集与 robots 规则

**事实**：Scrapy 提供按域并发、下载间隔、超时、体积上限及 robots 策略设置；不能只依赖不同运行入口的默认配置。[Scrapy 设置](https://docs.scrapy.org/en/latest/topics/settings.html) Playwright 支持隔离的浏览器上下文及同步、异步操作。[Playwright 上下文](https://playwright.dev/python/docs/browser-contexts)

**建议**：采集顺序采用官方导出/API、普通 HTTP、必要时浏览器渲染。每个来源提供独立解析器，统一保存获取地址、重定向结果、获取时间、响应摘要、内容散列、许可元数据和解析版本。抓取与解析解耦，保留原始快照供重新解析；内容去重也要保留各自出处。浏览器作业另设进程与并发预算，显式启用 robots 策略。

**事实**：RFC 9309 要求遵循成功获取的可解析规则；区分 robots 文件 unavailable（如 4xx）与 unreachable（网络或 5xx），后者通常必须按全部禁止处理，规范另有长期不可达例外。缓存一般不应超过 24 小时，文件不可达时除外；robots 规则不是访问授权。[RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html)

**建议**：将采集策略与许可状态分别存储；抓取端记录规则快照、判定及失败原因，对限流进行退避。4xx 分类的规范描述不应实现成对登录限制或封禁的自动绕过。

## 6. 工作流可靠性与运行环境

**事实**：LangGraph 的 checkpointer 保存线程内状态，store 保存跨线程数据。[持久化](https://docs.langchain.com/oss/python/langgraph/persistence) 恢复时受影响节点可能从函数开头重跑；任务结果可由检查点恢复，但副作用仍需幂等，修改任务/中断顺序可能破坏恢复匹配。[Graph API 恢复语义](https://docs.langchain.com/oss/python/langgraph/graph-api#re-execution-and-idempotency)

**建议**：把工作流状态与业务证据账本分开。作业以输入散列、算法/模型版本组成幂等键；事务内记录结果和待发送事件，队列消费者按键去重。配置租约、重试次数、失败状态和人工恢复入口。checkpoint 不等于外部服务和业务数据库具有“恰好一次”副作用；恢复也不保证重新调用模型会产生相同内容。

**事实**：Docker 默认没有 CPU/内存限制，Linux 资源控制依赖宿主机能力及 cgroup；内存不足可能触发进程终止。[容器资源限制](https://docs.docker.com/engine/containers/resource_constraints) OpenTelemetry 提供 traces、metrics、logs 等观测信号。[可观测信号](https://opentelemetry.io/docs/concepts/signals/)

**建议**：生产采用 Linux 容器，开发可继续使用 macOS；显式配置 API、数据库、浏览器与模型 worker 的资源和连接池预算，支持优雅退出、持久数据卷、备份恢复及失败作业重领。初期单机部署即可。贯通 `run_id`、史料版本与论断 ID，观察检索延迟、队列积压、重试、引用失败和人工审核量；运行日志不能代替长期保留的证据记录。
