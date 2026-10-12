# EvidHist 相关项目与产品版图

核验日期：**2026-10-10，Asia/Shanghai**。原创分析文档采用本项目 CC BY-NC-SA 4.0；所链接代码、数据、史料与产品继续适用各自许可。

## 1. 研究问题、范围与证据口径

本次研究寻找与 EvidHist **目标一致、目标包含或部分重合**的开源项目、公开代码研究项目、学术平台和商业产品。比较基线为 [README](../../README.md) 的完整目标：中文文言文及近现代史料基础设施，论断绑定来源、文本版本和原文位置，多源互证及来源独立性，冲突保留，不确定性和证据强度，可追溯生成，时空与知识图谱，以及有证据的历史推理。EvidHist 当前 v0.1 工作台与上述完整设计目标分开看待。

这里的“包含”需要区分两种含义：**包含 EvidHist 的某些功能子目标**，不等于**包含 EvidHist 的全部目标**。通用研究平台覆盖文献、证据和图谱，不足以自动证明它能完成中文历史史料批判。本次没有核实到一个公开项目或商业产品完整覆盖全部目标；这是对本次检索证据的判断，不是“全网不存在”或首创性结论。

检索覆盖中英文搜索、官方仓库与许可、机构官网、产品文档和作者论文。搜索主题包括历史研究 Agent、古籍数据库、史料结构化、来源批判、论证图谱、引文核查、历史时空、人文数据管理、定性分析和档案工作流。优先采用一手来源；论文成绩、官网能力声明、产品实际可用性与本次实测结果分别对待。

主表共 **50 个项目或产品家族**：第 3 节 8 项、第 4 节 9 项、第 5 节 8 项、第 6 节 6 项、第 7 节 11 项、第 8 节 8 项。HistAgent/HistBench、AI Historian/Westlake Historian、MARKUS/Comparativus 及同厂商数据库家族各按一项计；两项作者和场景不同的 HistoRAG 分开计。50 不是开源项目数，也不是独立竞品数量，标准和扩展阅读不计入。

**本次实际做了网页和仓库文档核验，没有安装、购买或登录这些产品，没有跑其模型、核实输出准确率或执行中文史料对照实验。** 表中的“事实”指一手资料明确描述的能力或许可，并不表示经过独立性能验证。“本次未见公开证据”保留未知状态，不能解释为确定不支持。公开代码、免费服务、开放数据、开源软件、收费托管是不同属性；代码许可不能替代史料和标注数据许可。

## 2. 最值得优先比较的项目

以下是依据后文来源作出的研究判断，而不是功能实测排名：

| 比较目的 | 重点对象 | 为什么接近 | 需要继续核查什么 |
| --- | --- | --- | --- |
| 中文专业历史研究完整流程 | 清史智能体 | 官方研发目标直接包含多源异构数据、互证、可追溯生成和可核验论证 | 产品访问、代码许可、版本原文定位、共同出处识别、冲突与未知状态的真实行为 |
| 可靠性验证与证据论证核心 | Isonomia | 明确论断、证据、推理、攻击关系、引用定位、共同根源追踪和可追溯写作；MIT | 早期平台的真实完成度；转载链方法能否迁移到古籍版本流传与史料转引 |
| 历史知识上下文与多观点论证工作台 | ResearchSpace | CRMInf 信念/论证，作者及时间归属、不同观点并存、PDF 证据片段、图谱和时间线 | 严格的不可变文本版本/定位契约、自动引文支撑核查、来源独立性与中文史料适配 |
| 有来源和不确定性的时空关系数据 | nodegoat | 来源引用、元素版本历史、不确定性、网络和时空分析 | 从结构化数据与人工标注延伸到自动互证及可追溯生成的实际工作量 |
| 中文人物时间线与跨文本依据 | AI Historian / Westlake Historian | 句级依据、TimeBlocks、跨文本验证、时间范围规范化及人工最终决策 | 通用论断、多种争议、史料依赖关系及版本学是否超出人物时间线范围 |
| 中文古籍整理与研究基础设施 | 识典古籍 | 免费平台覆盖 OCR、实体、多版本校勘、图文对照及研究助手 | 所有来源和许可的导出方式，以及可靠性核心是否形成可检查闭环 |
| 中文个人史料工作台与并列对读 | DocuSky | 个人建库、标注、探勘、GIS 与时间锚点对读，贴近材料整理到研究任务 | 不可变版本契约、互证独立性、冲突和未知状态的真实实现 |
| 历史来源批判与检索方法 | HistoRAG（柏林洪堡大学） | 把史料发现/选择与解释分开，强调检索的时间分布、可争议判断与研究者解释 | 软件许可、方法真实效果及中文史料的版本/共同出处处理 |
| 引用支持/反对与证据回查交互 | scite、Consensus、MAXQDA | 支持/反对证据、原文片段或编号引文回查，是 EvidHist 核查界面的直接参照 | 论文立场、编码或模型回答不能直接转为历史事实结论；传统史料适配仍未知 |

**定位判断：** 历史问答与自动摘要已有许多项目；真正值得比较的是“材料—版本—原文位置—论断—支持/反对证据—推断—未决状态”这条链。ResearchSpace 和 Isonomia 说明证据论证也已有相当接近的实践，不能把它排除在竞品研究之外。EvidHist 若继续推进，应以中文史料和可验收的来源独立性、版本定位及未知状态行为说明价值，而非泛称历史领域没有同类工具。

## 3. 历史研究 Agent 与专业平台

| 项目 | 一手资料明确描述的事实 | 与 EvidHist 的关系与缺口（判断） | 项目性质与许可 |
| --- | --- | --- | --- |
| **清史智能体** | 中国人民大学介绍结构化处理编年、地理、制度、传记、图像、论文、著作等多源材料，以互证、可追溯生成、机制解释和可核验论证为目标；2026-09-07 大学新闻记载 9 月 5–6 日会议发布 1.0 及数字清史共享平台。[研发介绍](https://iqh.ruc.edu.cn/xwdt/b50f66c6df364d80b40614a479c10e9f.htm)、[大学新闻](https://news.ruc.edu.cn/2096853452563124226.html) | **领域与总体研究方向高度一致**。本次未见公开证据确认来源独立性审计、逐论断不可变版本定位、冲突/未知完整闭环。 | 高校专业研究平台；公开发布不等于代码开源或任何人可直接访问，本次未核实软件许可。研发页重定向失败，功能依据官方搜索索引；1.0 发布依据直接读取的大学新闻正文。 |
| **HistAgent / HistBench** | 作者仓库提供历史问答 Agent，工具涉及档案/文献检索、OCR、图像、文档解析、翻译及引文元数据；HistBench 是配套多语言、多模态历史研究评测。[仓库](https://github.com/CharlesQ9/HistAgent)、[论文](https://arxiv.org/abs/2505.20246) | 历史检索、材料处理与推理重合。没有把 QA 基准准确率当成 EvidHist 的引用、冲突、独立性和不确定性指标；本次未见完整长期证据工作台的公开证据。 | 学术研究实现，代码 Apache-2.0；评测材料另核许可。[代码许可](https://github.com/CharlesQ9/HistAgent/blob/main/LICENSE) |
| **AI Historian / Westlake Historian** | 官方当前仓库描述从分散传记叙述生成可追溯人物—时间证据：句级处理、TimeBlocks、排序、跨文本证据验证、时间范围规范化；平台支持依据检查、修订记录与人工最终决策。[仓库与平台说明](https://github.com/YiFengLu1999/AI-Historian)、[平台](https://westlakehistorian.com/) | 时间线和跨文本核查**高度重合但范围较窄**。本次未见通用论断验证、来源谱系独立性或全类争议判定的公开证据。 | 学术开源实现 Apache-2.0；研究文本和数据另有条件，不能因代码开源自动复用全部语料。[数据条款](https://github.com/YiFengLu1999/AI-Historian/blob/main/data-licenses.md) |
| **Chronos** | 面向历史研究者协作抽取原始史料中的结构化数据；支持 PDF、图像和文本导入、页图查看及 Agent 会话。[仓库与使用说明](https://github.com/ai-historian/chronos) | 材料处理、抽取和人工检查重合；本次未见自动冲突、独立性或史实核查闭环的公开证据。 | **公开代码、非商业用途许可，不归通常意义的开源软件**。PolyForm Noncommercial 1.0.0，商业用途需另行许可。[许可](https://github.com/ai-historian/chronos/blob/main/LICENSE) |
| **HeuriTab / heuritab** | README 描述任意历史 JSON 语料的编辑、过滤、RAG 检索及逐项批量抽取，属于 Beta。[官方仓库](https://github.com/j-sheik/heuritab) | 历史语料管理和模型抽取重合；本次未见不可变版本定位、冲突和依赖来源审计的公开证据。 | 公开研究软件；README 正文声明 CC0 1.0 Universal，未见单独 LICENSE；具体代码、示例语料与第三方组件适用边界待核，不能从仓库侧栏没有许可直接判断无许可。 |
| **HistoRAG（Kim-Baumann / Hiltmann，柏林洪堡大学）** | 框架将史料发现/选择与解释分阶段，按历史时期时间窗口平衡检索，强调透明、可争议的判断与生成作为解释提议；Zenodo 提供 v0.1.0 软件发布。[官网](https://historag.org/)、[作者论文](https://arxiv.org/abs/2606.18103)、[软件发布](https://zenodo.org/records/20558762) | **来源批判、研究者判断与可追溯生成高度重合**；本次未见中文史料与来源流传独立性完整验证的公开证据。 | 学术软件/方法项目，已确认公开软件发布；[GitLab](https://scm.cms.hu-berlin.de/digital-history/digital-history-forschung/histo_rag/historag) 本次无法读取，代码许可待核，不贸然标 MIT 或开源。 |
| **HistoRAG（Duan / Guo，地方史教学）** | 独立的同名论文项目：VLM 转写史料并保留行级置信，混合检索、关系数据库、实体密集段图谱、卷页引文及教学聊天回查。[2026 年 9 月预印本](https://arxiv.org/abs/2609.29184) | **地方史料整理、证据定位和问答重合**；论文提出架构不等于商业或学术平台实际可用，本次未见来源独立性全流程公开证据。 | 学术论文项目；代码、软件许可、产品可用性待核，论文许可不能替代软件许可。须与上一项消歧。 |
| **BiographyNet** | 从人物传记构建语义知识库，关联人物、事件和关系并支持网络/地图/时间线；作者论文强调资料及 NLP 处理 provenance 和解释的不确定性。[项目介绍](https://ucds.cs.vu.nl/biographynet-project/)、[论文](https://aclanthology.org/L14-1078/)、[后续方法论文](https://arxiv.org/abs/1801.07073)、[仓库](https://github.com/cltl/BiographyNet) | **历史人物抽取、处理溯源和不确定性高度重合**；本次未见中文史料、引文支持与独立性验证完整公开证据。 | 学术历史数据/处理项目，公开 NLP 工具和数据；本次仓库未找到明确许可，标待核。 |

## 4. 证据、论证与人文数据工作台

| 项目 | 一手资料明确描述的事实 | 与 EvidHist 的关系与缺口（判断） | 项目性质与许可 |
| --- | --- | --- | --- |
| **ResearchSpace** | 用语义图谱表示上下文；CRMInf 描述信念及论证，陈述可归属作者与时间，不同证据和视角可并存比较；PDF 片段可嵌为引用，还提供知识地图和时间线。[语义工具](https://researchspace.org/semantic-tools/)、[仓库](https://github.com/researchspace/researchspace) | **包含证据论证、观点保留、图谱和时空等重要子目标**。本次未见中文语料、来源独立性自动核查及 EvidHist 式引用契约的完整公开证据。 | 人文/文化遗产开源平台，官方仓库说明 AGPL-3.0-or-later；依赖和数据另核。 |
| **Isonomia** | 官方描述论断版本、证据和攻击关系；引文跳转页/片段/图/章节；浏览器核查论断与引文是否相符、沿转载链识别漂移和共同根源；图谱支撑可追溯写作。[官网](https://www.isonomia.app/)、[仓库](https://github.com/Iso-nomia/Isonomia) | **可靠性核心高度重合**，尤其共同根源和反证关系；官方自称早期平台。本次未见中文史料库、古籍版本流传方法及历史研究真实评测的公开证据。不能把形式论证成立当作史实为真。 | 通用论证/验证平台，MIT 开源；以上为作者声明，本次没有实测。[许可入口](https://github.com/Iso-nomia/Isonomia/blob/main/LICENSE) |
| **nodegoat** | 自定义研究数据、网络及可视化，支持对象来源引用和元素版本历史；官方专门说明历史材料缺失时的不确定性表示。[来源引用](https://nodegoat.net/guide.p/448.m/19/add-source-references)、[不确定数据](https://nodegoat.net/blog.s/43/how-to-store-uncertain-data-in-nodegoat-incomplete-source-material)、[介绍](https://nodegoat.net/about) | **研究工作台、来源、不确定性和时空关系高度重合**。本次未见自动史实互证、生成内容幻觉核查的完整公开证据。 | 人文开源软件与服务，AGPLv3。[官方仓库](https://github.com/nodegoat/nodegoat)。须与 OWASP 的同名 NodeGoat 安全演示区分。 |
| **Heurist** | 人文研究者自行构建、管理、分析、发布结构化数据库；可关联 Zotero 书目，提供地图、时间线、关系图及归档导出。[官方介绍](https://heuristnetwork.org/)、[仓库](https://github.com/HeuristNetwork/heurist) | **包含史料结构化、实体关系、检索与可视化等子目标**。本次未见原文支持性、冲突裁定或来源独立性自动核查的公开证据。 | 非营利人文开源平台及免费托管，GPL-3.0。[许可证](https://github.com/HeuristNetwork/heurist/blob/h7dev/LICENSE_gnuGPL3.txt) |
| **Wikibase** | 协作管理版本化结构化数据；Statement 包含 claim、qualifier、reference 和 rank，支持不同值及限定条件；reference 可以为空。[数据模型](https://www.mediawiki.org/wiki/Wikibase/DataModel)、[官网](https://www.mediawiki.org/wiki/Wikibase) | **包含论断—来源—限定条件建模子目标**。来源不是强制，rank 也不是证据强度或真值保证；本次未见中文历史自动验证的公开证据。 | 通用开源知识库工具，Wikibase Repository GPL-2.0-or-later；数据许可由各实例决定。[软件许可](https://www.mediawiki.org/wiki/Extension:Wikibase_Repository) |
| **FactGrid** | 用 Wikibase 为历史研究管理多语言知识图谱，实体有持久标识，陈述变化有版本记录；数据 CC0。[机构介绍](https://www.uni-erfurt.de/en/forschungszentrum-gotha/forschung/focus-areas-of-research/digital-humanities/factgrid)、[现行条款](https://database.factgrid.de/wiki/FactGrid:Terms_of_Service) | **历史领域知识与来源管理重合**；Wikibase 实例不等于自动可靠性引擎。本次未见中文史料依赖审计和可追溯生成全流程的公开证据。 | 学术协作开放数据平台；数据 CC0，底层 Wikibase 适用其软件许可。 |
| **Seshat: Global History Databank** | 汇集历史社会变量，并以研究者/专家编码；官方工作方法要求尽量记录文献或专家分歧、不确定性，使分析能够纳入替代解释。[工作方法](https://seshatdatabank.info/how-we-work) | **争议、未知与历史证据编码高度重合**，很适合参考状态和人工判定依据；本次未见逐论断自动验证/中文专用的公开证据。 | 全球历史学术数据库；本次未核实全平台代码或所有数据的统一许可，使用具体数据包前另核。不要与同名 Agent/软件项目混淆。 |
| **Gramps** | 家谱研究中分开 Source 与可复用 Citation；Citation 可记录卷页、日期、笔记、图片和 Confidence。Normal 可能代表尚未评估/尚未验证，官方明确置信等级不能替代使用者评估。[6.0 手册](https://gramps-project.org/wiki/index.php/Gramps_6.0_Wiki_Manual_-_Entering_and_editing_data:_detailed_-_part_2) | **来源、引文位置、证据强度及未核查状态重合**；家谱范围较窄。本次未见跨史料自动冲突与生成核查的公开证据。 | 开源家谱软件，GPL-2.0-or-later。[项目许可](https://www.gramps-project.org/wiki/index.php/Project_License) |
| **Argüman** | 用 because、but、however 等关系构建支持与反对的论证图。[官方仓库](https://github.com/arguman/arguman.org) | **论断分歧和论证图重合**；本次未见史料版本、原文支持核查和中文历史数据的公开证据。 | 开源论证软件；LICENSE 是 AGPLv3，但 README 泛称 GPLv3，存在不一致，复用前核对适用许可。[LICENSE](https://github.com/arguman/arguman.org/blob/master/LICENSE) |

## 5. 标注、材料整理、版本比对与文化遗产工具

| 项目 | 一手资料明确描述的事实 | 与 EvidHist 的关系与缺口（判断） | 项目性质与许可 |
| --- | --- | --- | --- |
| **Recogito** | 语义标注文本/图像、把地名与 gazetteer 关联、导出 Linked Data，并跟踪标注 provenance 与版本历史。[官网](https://recogito.pelagios.org/)、[FAQ](https://recogito.pelagios.org/help/faq) | **原文标注、地点对齐、来源追踪子目标重合**；本次未见论断证据强度或自动互证的公开证据。 | 开源软件 Apache-2.0；官方托管条款将标注以 CC0 公开，上传材料版权另行保留。[软件许可](https://recogito.pelagios.org/help/about)、[服务条款](https://www.recogito.pelagios.org/help/terms) |
| **INCEpTION** | 多层文本标注、知识库实体链接与机器辅助建议。[官方仓库](https://github.com/inception-project/inception)、[文档](https://inception-project.github.io/) | **实体、关系标注与人工复核重合**；本次未见历史事实论断、来源独立性和全流程核查的公开证据。 | 学术开源语义标注平台，Apache-2.0。 |
| **Arches** | 面向文化遗产清单和管理的地理信息系统，用于遗址、历史建筑、景观等资源。[官方仓库](https://github.com/archesproject/arches)、[官网](https://www.archesproject.org/) | **异构遗产数据、关系和地理可视化子目标重合**；本次未见文本史料的论断核查或多源互证全流程公开证据。 | 文化遗产开源平台，仓库 AGPL-3.0；数据与具体应用另核。 |
| **Tropy** | 为档案研究照片建立资料项、自定义元数据、标签、笔记、转录与图像细节选区。[官网](https://www.tropy.org/)、[元数据手册](https://docs.tropy.org/before-you-begin/metadata) | **材料—档案位置—注释整理重合**，可参考避免图片与出处脱离；本次未见自动史料判断公开证据。 | 开源档案照片工作台，AGPL-3.0。[LICENSE](https://github.com/tropy/tropy/blob/main/LICENSE) |
| **Omeka S** | 为高校、图书馆、档案和博物馆管理共享资料项、媒体及元数据并发布独立展览。[官方仓库](https://github.com/omeka/omeka-s)、[手册](https://omeka.org/s/docs/user-manual/) | **史料收藏、结构化与发布子目标重合**；本次未见论断互证、独立性或冲突验证的公开证据。 | 开源数字收藏出版系统，GPLv3；托管、模块和材料另核。 |
| **CollateX** | 对至少两个文本版本分词和对齐，识别差异与移位，输出结果供校勘记或文本源流分析使用。[官方仓库](https://github.com/interedition/collatex) | **版本比对高度重合**，可作为共同文本与异文分析参照；字符串相似不能单独证明来源依赖。本次未见史实验证的公开证据。 | 开源文本校勘组件，GPL-3.0。[LICENSE](https://github.com/interedition/collatex/blob/master/LICENSE.txt) |
| **史记知识库 / shiji-kb** | 将《史记》实体、历史事件和关系组织为交互知识图谱；作者明确限于《史记》文本内容，不涉及史实考证，并说明 AI 标注可能有错误。[官方仓库](https://github.com/baojie/shiji-kb) | **中文古代实体与事件图谱高度重合**；它自身明确的边界说明“文本记载”与“史实考证”须分开，不能作为已经实现互证的证据。 | 脚本 MIT；标注数据 CC BY-NC-SA 4.0；仓库声明《史记》原文公有领域，实际数字文本版本仍需逐项核对来源。 |
| **CHisIEC** | 作者发布中国古代史料 NER/RE 数据及实验代码，实体数据用 CoNLL，关系数据用 JSON。[仓库](https://github.com/tangxuemei1995/CHisIEC)、[论文](https://arxiv.org/abs/2403.15088) | **中文史料实体与关系抽取子目标重合**；这是语料/实验资源，本次未见完整产品和可靠性核查的公开证据。 | 学术公开代码与数据；本次未在仓库根目录或 README 找到明确使用许可，标为待核，不直接称开源。 |

## 6. 中文史料平台与商业资料数据库

商业产品表中的性质仅反映官方介绍的运营/服务方式；没有核实开放代码许可的产品不标成开源，也不据此断言所有组件均闭源。价格、语料规模和发布计划不作比较依据。

| 项目或产品家族 | 一手资料明确描述的事实 | 与 EvidHist 的关系与缺口（判断） | 项目性质与使用条件 |
| --- | --- | --- | --- |
| **识典古籍** | 整理平台包括 OCR、标点、实体识别、多版本校勘和翻译；研究平台列图文对照、字典百科、实体关系地图及深度研究助手。[官网](https://www.shidianguji.com/zh/)、[官方公益介绍](https://gongyi.bytedance.com/issue/7160869621275363364/7160869621275379748?page_from=header) | **中文史料整理研究流程高度重合**；本次未见来源独立性审计、冲突与未知状态完整闭环的公开证据。 | 企业公益与高校合作的免费开放平台；免费不等于开源，代码与史料再利用许可另核。 |
| **全历史 / 全知识** | 官网列历史年表、时空地图、关系图谱和 AB 路径。[官网](https://speed.allhistory.com/)、[关系图谱入口](https://www.allhistory.com/relationindex) | **关系路径及历史时空可视化高度重合**；本次未见逐条关系的原文证据、独立性或因果核查的公开证据。 | 企业历史知识产品；未核实开放代码许可或具体价格。 |
| **瀚堂典藏** | 提供古籍和近代报刊，图文同步、全文精准/模糊检索。[官网](https://www.hytung.cn/default.aspx) | **中文古代/近代史料基础设施重合**；本次未见自动论断核查的公开证据。 | 商业专业数据库；按订购与材料条款使用，代码/数据开放许可未核实。 |
| **爱如生数据库家族** | 官网列中国基本古籍库、中国方志库、申报等，提供全文/主题检索、图文对照以及机构/个人版。[当前官方入口](https://er07.com/) | **中文史料供给与原文检索高度重合**；本次未见冲突或来源独立性验证的公开证据。 | 商业专业数据库；各库访问、复制、批量获取条件另核。旧域名访问失败，不据此推断产品失效。 |
| **籍合网 / 中华经典古籍库** | 官方首页列古籍、工具书、古籍书目、石刻、晚清民国文献，以及历史人物/事件专题入口。[官网](https://www.ancientbooks.cn/) | **史料、书目及主题检索重合**；本次未见自动史实可靠性验证的公开证据，不加入未核实的 AI 或校勘宣传。 | 商业出版数据库家族；具体材料、下载及再利用条件另核。 |
| **East View 中国资料数据库家族** | 《东方杂志》1904–1948 全文影像、人物/主题索引与布尔检索；官方说明不能与其他 TKN 资源跨库检索。目录另列地方志全文及图像。[东方杂志](https://www.eastview.com/resources/journals/eastern-miscellany/)、[官方目录](https://www.eastview.com/evasiancatalog/) | **近现代资料及方志基础设施重合**；本次未见论断/版本/独立性自动验证的公开证据，不能默认各数据库互通。 | 商业数据库与资料服务；按具体订购和材料许可使用。 |

## 7. 商业研究、引文核查与定性分析产品

| 项目或产品 | 一手资料明确描述的事实 | 与 EvidHist 的关系与缺口（判断） | 项目性质与使用条件 |
| --- | --- | --- | --- |
| **Gale Digital Scholar Lab** | 建立原始文献语料集，清洗、文本挖掘、可视化、导出与协作。[产品介绍](https://www.gale.com/cn/product-catalog/digital-humanities-tools/gale-digital-scholar-lab)、[官方流程说明](https://blog.gale.com/gale-digital-scholar-lab-removing-barriers/) | **采集整理—研究分析流程重合**；本次未见中文专用史料验证或自动史实裁决的公开证据。 | 面向订阅机构的商业数字人文平台；语料来源和导出条件另核。 |
| **Transkribus** | 历史手写/印刷识别、校订、实体标签、全文模糊搜索、页定位和匹配高亮，支持导出与公开集合。[功能帮助](https://help.transkribus.org/what-can-you-do-with-transkribus)、[搜索](https://www.transkribus.org/search) | **史料采集、整理、检索重合**；EvidHist 目前以已有文本为主。本次未见历史论断冲突和独立性验证的公开证据。 | 合作社运营的免费及订阅服务；不因服务免费或模型公开就视整个平台为开源，材料许可另核。 |
| **scite** | Smart Citations 显示引用的支持/反对关系，AI 回答可定位论文具体句子。[官网](https://scite.ai/) | **论断支持/反对证据及回查交互高度重合**；引用立场不等于历史事实判定，本次未见古籍版本流传和来源独立性验证的公开证据。 | 商业科研证据产品；软件开放许可及语料再利用许可未核实。 |
| **Elicit** | 系统综述包含检索、摘要筛选和全文数据抽取，官方方案展示逐句引用报告。[流程说明](https://elicit.com/blog/systematic-review/)、[系统综述方案](https://roche.elicit.com/solutions/systematic-review) | **检索、提取、整合和证据报告重合**；本次未见中文古籍处理和史料共同出处审计的公开证据。 | 商业论文研究工作流；使用与语料条件另核。 |
| **Consensus** | 官方说明研究检索综合、引文图谱、可用时原文段落、支持/不支持/混合立场，以及证据不足时的说明。[检索原理](https://help.consensus.app/en/articles/9922673-how-consensus-works)、[引文与分析](https://help.consensus.app/en/articles/17234045-consensus-ai-analysis-citations-and-visuals) | **证据综合、分歧及不确定表达高度重合**；本次未见中文史料版本与独立性验证的公开证据。 | 商业科研产品；不把基于论文的共识分布当成历史论断真假裁决。 |
| **NotebookLM / Gemini Notebook（抓取名称）** | 本次 Google 官方帮助 URL 重定向到 Gemini Notebook：基于选定材料回答，提供文本/图片引文，悬停可看原文、点击可看上下文，笔记可保留可点击引文。[官方帮助](https://support.google.com/gemininotebook/answer/16179559?hl=en) | **来源限定问答、原文回查与引文笔记重合**；本次未见来源依赖、版本学及冲突证据裁定的公开证据。URL/页面名称变化不是完整改名公告，本报告保留两名称说明抓取状态。 | 企业托管产品；本次未查价格或开放代码许可。 |
| **MAXQDA / AI Assist** | AI Chat 使用编号引用返回来源；AI 可辅助编码、汇总多个片段与改写。[AI Chat](https://www.maxqda.com/help/ai-assist/ai-chat?view=full)、[AI Assist 说明](https://help.maxqda.com/en/support/solutions/articles/80001135283-what-is-maxqda-ai-assist-) | **原文片段—研究判断及可追溯查询高度重合**；本次未见史料来源独立性和史实自动验证的公开证据。 | 商业定性研究产品；AI Assist 和材料使用另受服务条件约束。 |
| **NVivo / NVivo AI Cloud** | 当前官方产品页描述材料导入、编码、跨案例模式、来源回查、审计轨迹及研究者接受/修改/拒绝；AI Cloud 是独立许可的浏览器服务。[产品页](https://lumivero.com/products/nvivo/)、[平台与许可](https://community.lumivero.com/s/article/NVivo-AI-Cloud-Platforms-Licensing-Usage-and-Security?language=en_US) | **研究工作台、编码和审计过程重合**；本次未见中文史料独立性/历史事实验证公开证据。当前可用性仅依据产品页声明，未登录实测，不以旧计划日期证明上线。 | 商业定性研究产品；桌面与 AI Cloud 许可不同。 |
| **ATLAS.ti** | 将段落转为 quotations 并自动编码；网络连接原文引文、编码及其他节点。[AI 编码](https://atlasti.com/ai-coding-powered-by-openai)、[网络文档](https://doc.atlasti.com/QuicktourWin/Networks/NetworksAboutNodesAndLinks.html) | **原文标注、证据片段和关系可视化重合**；本次未见历史自动互证和来源独立性验证的公开证据。 | 商业定性研究产品；引用/编码关联不等于支持性核查已经完成。 |
| **i2 Analyst's Notebook / i2 Analyze** | 多源结构/非结构资料导入，实体、关系、事件、时间线和社会网络分析；实体/关系可记录 source/reliability，Analyze 可记录来源位置、名称、类型、图像。[产品](https://i2group.com/solutions/i2-analysts-notebook)、[属性](https://docs.i2group.com/anb/10.1.2/properties.html)、[来源引用](https://docs.i2group.com/analyze/4.4.6/implementing_source_references.html) | **包含多源调查、来源可靠性、图谱和时间线等子目标**，跨领域范围更广；本次未见中文史料版本、来源独立性审计与未知状态完整闭环公开证据，不能判断包含 EvidHist 全部目标。 | 商业调查分析工作台；本次未核实软件开放许可或实际历史任务效果。 |
| **Aeon Timeline** | 官方有历史研究时间线与人物/事件关系整理指南。[古代史指南](https://www.aeontimeline.com/3-4-guides/ancient-history) | **历史时间线和事件关系重合**；所用指南属于 3.4 旧版，不能推断当前版本具备全部旧版行为；本次未见引用核查与不确定性验证公开证据。 | 商业时间线软件；不以旧指南替代当前版本实测。 |

## 8. 中文历史资料与工具基础设施

以下资料和工具可以成为 EvidHist 的来源或工作流参照；收录不表示已经接入，也不表示允许批量抓取、再分发或商业使用。

| 项目或工具家族 | 一手资料明确描述的事实 | 与 EvidHist 的关系与缺口（判断） | 项目性质与许可 |
| --- | --- | --- | --- |
| **CBDB / 中国历代人物传记资料库** | 面向中国历史人物传记关系、社会网络和空间分析。[官网](https://cbdb.hsites.harvard.edu/) | **人物消歧、关系与历史研究底层数据高度重合**；本次未见全文论断支持、来源独立性及生成核查闭环公开证据。 | 学术数据库。2026-08-20 生效的条款分层：指定单机版日期/数据量范围内 CC BY-NC-SA 4.0；更新或范围外数据适用独立 CBDB 条款，含非商用、禁止演绎、禁止再分发或公开查询服务，不能写成全部开放数据或一概 CC BY-NC-ND。[现行许可](https://cbdb.hsites.harvard.edu/cbdb-data-licensing-terms) |
| **CHGIS / 中国历史地理信息系统** | 历史地点、时段/名称及行政层级查询；官方发布 V6。[数据库说明](https://chgis.fas.harvard.edu/pages/database/)、[V6 数据与许可](https://chgis.fas.harvard.edu/data/chgis/v6/) | **历史地名、行政沿革、时空底层高度重合**；本次未见史料论断可靠性引擎公开证据。 | 学术历史地理数据库；V6 页明确免费学术研究使用，禁止商业用途、转售和再分发。许可按版本确认，不从其他版本外推。 |
| **Ctext / 中国哲学书电子化计划** | API 提供章节 URN、原文/元数据导出与插件接口，存在条款及认证限制；文本工具提供 n-gram、相似/差异、网络及脚本记录。[API](https://ctext.org/tools/api)、[文本工具](https://ctext.org/plugins/texttools/) | **中文文本基础设施、章节回查、复用比较重合**；文本相似和章节 URN 不足以证明来源独立性或历史论断，本次未见完整验证闭环公开证据。 | 学术数字文本平台；不默认开源，开放访问不等于所有文本与 API 可自由批量再利用。 |
| **MARKUS + Comparativus** | 中文人地名、时间、官职等自动/人工标注，外部工具链接和 TEI/可视化导出；Comparativus 检测文本重合/复用，显示正文、表格、弦图并导出 TSV/JSON。[MARKUS](https://dh.chinese-empires.eu/markus/beta/index.html)、[仓库](https://github.com/dHumanities/markus)、[Comparativus](https://dh.chinese-empires.eu/comparativus/)、[匹配算法](https://github.com/dHumanities/markus/blob/master/comparativus/algorithm.md) | **中文史料标注和共同文本识别高度重合**；匹配可产生同源候选，但不能直接验证独立性或决定互证权重。 | 学术开源工具家族，代码 AGPL-3.0-or-later，官网文档/视频 CC BY-SA 4.0；输入材料另核。 |
| **LoGaRT** | 面向中国地方志的搜索、提取、分析与时空统计可视化。[机构研究工具页](https://www.mpiwg-berlin.mpg.de/research-websites)、[研究系列](https://www.mpiwg-berlin.mpg.de/logart-short-paper-series) | **中文地方志的材料到研究分析流程高度重合**；本次未见论断冲突及来源独立性完整验证公开证据。 | 学术历史研究工具，代码许可待核。机构工具页所列 Harvard-Yenching 稀见地方志合作语料为 CC BY-NC-ND 4.0，不能外推到所有 LoGaRT 材料。 |
| **DocuSky** | 个人史料建库、格式转换、标注、探勘、GIS、文本对读；官网案例“春秋三传对读”按时间锚点并列，另有段落引文、批注和校订资料。[官网](https://docusky.org.tw/)、[工作台介绍](https://docusky.org.tw/DocuSky/home/v4/) | **中文史料工作台高度重合**，尤其材料建库与对照阅读；本次未见来源独立性审计、不可变版本定位及冲突/未知闭环公开证据。 | 学术服务平台，公开访问不等于开源；材料许可按库，官网机构收费方案不据此认定已经商业落地。 |
| **Kanripo / Kanseki Repository** | Git 托管汉籍，目录分经史子集道佛及正史/编年/地理等；版本文本页可含版次、卷页及影像链接。[目录仓库](https://github.com/kanripo/KR-Catalog)、[官方仓库群](https://github.com/orgs/kanripo/repositories)、[版本文本示例](https://krx.kanripo.org/edition/SBCK/KR2m0054/032) | **可版本化史料源及原文位置高度重合**；Git 版本和引用位置是必要基础，本次未见自动论断验证公开证据。 | 公开汉籍文本基础设施；示例页制作内容标 CC BY-SA，未明版本，不能用目录或示例许可覆盖全部版本、影像和史料。 |
| **CBETA** | 发布 TEI P5 XML 佛典文本，并有正式引用复制规范；FAQ 说明材料授权随藏经/出版单位而异。[XML 仓库](https://github.com/cbeta-org/xml-p5/blob/master/README.md)、[引用规范](https://archive2.cbeta.org/node/5128)、[FAQ](https://cbeta.org/faq) | **校订文本、精确位置引用和版本归档重合**；佛典范围更专，本次未见通用历史互证或事实验证公开证据。 | 公益佛典与公开 XML 数据基础设施；代码与资料分别判断，不能一概称开放数据。copyright 页面本次访问失败，使用具体藏经前继续核许可。 |

## 9. 比较矩阵与下一步

矩阵比较八个功能维度，依据仅为前文链接的一手资料：**明** = 有较直接的能力描述；**部** = 有相关部分能力，未覆盖完整要求；**?** = 本次未见足够公开证据。它不代表安装测试、效果评分或成熟度。尤其“互证/独立”要求同时比较来源和识别共同出处，不能把检索多个文件直接计作“明”。

| 项目 | 中文历史 | 材料基础设施 | 来源/版本/位置 | 互证/独立 | 冲突/反证 | 不确定/强度 | 可追溯生成/推理 | 图谱/时空 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 清史智能体 | 明 | 明 | 部 | 部 | ? | ? | 明 | 部 |
| Isonomia | ? | 部 | 明 | 明 | 明 | 明 | 明 | 部 |
| ResearchSpace | ? | 明 | 部 | 部 | 明 | 明 | 部 | 明 |
| nodegoat | ? | 明 | 部 | ? | 部 | 明 | ? | 明 |
| AI Historian | 明 | 部 | 部 | 部 | ? | 部 | 明 | 部 |
| 识典古籍 | 明 | 明 | 部 | ? | ? | ? | 部 | 明 |
| DocuSky | 明 | 明 | 部 | 部 | ? | ? | ? | 明 |
| scite | ? | 部 | 部 | 部 | 明 | 部 | 明 | ? |
| NVivo | ? | 明 | 部 | 部 | ? | ? | 部 | ? |

“来源/版本/位置”的完整要求包括具体文本版本、原文位置和支持性核查。Isonomia 的页/片段引用、快照和来源支撑检查在公开声明上较直接，但仍未证明传统史料版本学适配。ResearchSpace 的来源片段、nodegoat 的数据版本、scite 的论文句子定位各有价值，也各自不等于这三个要求全部达成。NVivo 的跨案例模式属于研究比较，不能直接计为独立来源验证。

下一轮可比较同一真实任务，而不是追加宣传功能清单：选取一个中文历史事件，保留至少两个不同文本版本、一条转引链、一项日期冲突、一项证据不足论断和一项明确推断，检查各工具能否完整回查、保留冲突、识别同源、显示未知并导出依据。这只是后续方案，本次未执行。

实现参照可拆为当前任务：DocuSky/Tropy/识典的材料整理；Recogito/INCEpTION/MARKUS 的原文标注；Wikibase/ResearchSpace 的陈述与语义关系；CollateX/Comparativus 的文本版本或复用候选；Gramps/Seshat 的未验证和争议编码；Isonomia/scite 的引文支撑与反证交互。选择参照不表示引入这些系统、照搬其模型或扩大 EvidHist 当前实现范围。

## 10. 许可与证据待核清单

1. **商业/非商业边界：** Chronos 的非商业许可、shiji-kb 标注数据、CBDB 分层条款、CHGIS V6 与各商业数据库材料条件需要在具体复用时登记；不能把可下载或 GitHub 公开视作 MIT 可用。
2. **许可待核：** CHisIEC、BiographyNet、两项 HistoRAG 的具体软件/数据许可；HeuriTab README 的 CC0 适用范围和第三方材料；Argüman README 与 LICENSE 的不一致；Seshat 全平台及具体数据包；Kanripo 的版本/影像；CBETA 各出版单位授权。
3. **能力待核：** 清史智能体公开发布后的访问条件；Isonomia 早期状态下共同根源、引文支撑、反证和未知行为；识典/DocuSky 的数据导出和许可；商业产品所谓 AI、来源回查或置信度是否对应可持久保存的研究依据。
4. **可复现性：** 本文为截至核验日的网页资料摘要，未保存全部页面内容/许可快照，也未固定全部上游 commit。实际集成或购买前需按版本重新核验，不能将本报告作为永久许可证明。

扩展阅读：[OWASP OOVS v0.1](https://github.com/OWASP/OWASP-Open-Source-Intelligence-Standard/blob/main/oovs/v0.1/standard.md) 与独立来源、矛盾和未知处理高度相关，但属于验证标准，不作为产品计数或已经落实的 EvidHist 设计；[HistBench](https://arxiv.org/abs/2505.20246) 属于评测依据，不以基准得分替代真实产品验收。一般 Agent 框架、普通聊天机器人和没有直接史料/证据功能的图表工具不纳入主表。

## 11. 核验记录、限制与变更摘要

本次查阅官方资料与仓库，未执行上述产品或模型。本研究包含搜索索引能够访问但正文抓取失败的机构资料，其证据层级已在对应行说明。未把项目自报成绩转写为 EvidHist 质量结果，也未抓取第三方史料或导入外部代码。

| 变更摘要项目 | 记录 |
| --- | --- |
| 计划范围 | 仅新增 `docs/research/related-project-landscape-2026-10-10.md`，记录相关项目、许可、一手来源、重合关系与未决问题。 |
| 实际改动 | 同计划；不修改 README、代码、依赖、API 契约或既有设计。 |
| 验证结果 | 官方资料人工核验已执行。`make check` 实际退出 0：Python 3.14.8、139 个快速测试通过，ruff、pyright、契约快照、提交策略配置、import-lint、deptry、pylint 通过，结构检查 0 failures / 7 warnings。这仅证明现有仓库快速门槛，不验证外部产品可靠性或调研事实；未运行外部产品、模型、付费功能或真实中文史料任务。文档无对应实现影响，未做数据库、系统、变异或安全检查。 |
| 发现但不碰 | README 现有项目参考未分别说明 Chronos 非商业许可、shiji-kb 代码/数据许可，后续可独立补充；CBDB 本次重核与既有 `docs/source-licensing-guidance.md` 分层条款一致，不列为文档缺陷。仓库检查有 7 个既有结构警告，本次不修改代码。HeuriTab 独立许可文件、CHisIEC 许可、Argüman 许可不一致等上游待核事项保持记录，不修改外部仓库。 |
