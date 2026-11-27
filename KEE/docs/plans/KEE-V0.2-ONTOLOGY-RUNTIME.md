# KEE V0.2 — Ontology Runtime 技术增强与研发实施规范

> 状态：Proposed / 待研发评审；文档版本 v0.2.0；编制日期：2026-11-27  
> 适用仓库：`vaelephant/300-6-KEE`（以 `KEE/` 为实际工程根目录）  
> 交付性质：**仅技术规划和研发验收规范，不代表已实现，不授权改动现有代码**  
> 对标参考：[TrustGraph](https://github.com/trustgraph-ai/trustgraph)（Apache-2.0）；参考其标准与契约，不直接引入整套服务。

## 0. 执行摘要与不可变约束

**产品定位**：KEE 是跨行业通用知识工程与语义运行底座；HCC-CIP 的肝癌诊疗知识属于独立行业应用/场景包，不能把医疗类、医疗表、临床路径判断硬编码进 KEE 通用内核。

**原则**：

1. **保留 KEE 的 Rust Crate + PostgreSQL/pgvector + Tantivy 主体架构**。V0.2 不引入 Cassandra、Qdrant、Pulsar/RabbitMQ，也不为每个功能创建微服务。
2. **遵守现有「开放语句 → 语义对齐 → 类型化事实」契约**：抽取阶段只记录原文陈述及证据，不在 LLM 抽取提示词强塞本体，不直接生成类型化事实；本体检查发生在**语义对齐/物化阶段**。此原则优先于对标项目的 OntologyRAG 实现习惯，任何更改须先提出 ADR 和回归实验。
3. **不可重写历史账本**：事实撤销、更正、规则版本、证据时间按已有双时态/附加记录处理；兼容历史 as-of 查询，禁止覆盖原有证据链。
4. **人工批准高风险写入**：低置信映射、冲突裁决、敏感策略变更、医疗规则变更必须经可审计审批。LLM 的解释不是医学证据或授权决定。
5. **无静默放行**：内部策略校验错误、缺失用户上下文、跨 KB 查询和授权解析失败一律 fail closed；审计可用性故障依风险等级进入显式拒绝/降级模式。
6. **许可证合规**：保留原始项目版权、NOTICE/许可证义务；不得把借鉴 TrustGraph 的标准设计描述为复制代码。上游 `deeplethe/utopia` 关系与后续自研代码的知识产权在正式交付前清点。
7. **开发边界**：本文件仅规定实施方案；各阶段必须通过测试门槛和 ADR 审核后才进入编码，不以「模块存在」替代「行为已验证」。

## 1. 当前基线与工程证据（2026-11-27 静态检查）

| 维度 | 源码/设计证据 | 当前判断 | V0.2 工作 |
| --- | --- | --- | --- |
| 领域本体 | `crates/kee-reason/src/ontology.rs`、`crates/kee-server/src/ontology_index.rs`、`docs/design/ontology.md` | 具备类、关系、约束与自洽性检测代码 | 约束测试覆盖 + 抽取后对齐统一契约 |
| 开放抽取/对齐 | `crates/kee-extract/src/open.rs`、`crates/kee-server/src/phrase_alignment.rs`、`migrations/0067_a_bound_statement_becomes_a_typed_fact.sql` | 已有开放抽取及后续对齐路径；须跑 E2E 核实 | 类型签名/领域约束的硬校验与拒绝原因 |
| 本体/推理 | `crates/kee-reason/src/rules.rs`、`derive.rs`、`docs/design/rules.md` | 有规则/前向派生代码 | 规则版本、前提、证明与拒绝路径回归 |
| 双时态账本 | `crates/kee-store/src/temporal.rs`、`record_axis.rs`、`docs/design/ledger.md` | 已设计双时间轴和证据行 | 所有新查询保留 `as_of`/有效时间语义 |
| 证据来源 | `crates/kee-ingest/src/provenance.rs`、`crates/kee-server/src/rdf.rs` | 原文/OCR/转写/描述区分，RDF 导出含 PROV-O | 串联检索、规则与回答 Trace |
| 身份与 KB 权限 | `crates/kee-store/src/access.rs`、`docs/design/access-and-audit.md` | 已有 KB RBAC、Token 作用域与审计 | 细化到实体/关系/属性/证据的读策略 |
| 文档/图谱检索 | `crates/kee-search`、`crates/kee-server/src/retrieval.rs` | 已有检索功能 | 有界路径扩展、类型/时间过滤、可解释截断 |
| RDF 互操作 | `crates/kee-server/src/rdf.rs`、`docs/decisions/0020-*.md` | 现有 Turtle/JSON-LD 导出 | 研究 SPARQL 子集，不承诺完整 SPARQL 1.1 |
| MCP/Agent | `crates/kee-server/src/api/mcp.rs`、`docs/design/chat-and-mcp.md` | 已有 MCP 服务 | 所有新读取入口统一接入权限/Trace |

**事实分级**：以上是源码静态检查与文档证据；「存在代码」不表示 E2E、压测、医院级安全验收已完成。此前设计文档中某些 `0044` 的阶段状态可能随最近迁移变化，实施前需要核对最新 `main` 上的实现与测试，不能依照旧描述覆盖当前契约。

## 2. V0.2 范围

### P0（必须）

- **OR-01 对齐阶段的本体约束**：候选 `(subject, predicate, object)` 应根据 domain/range、继承、互斥、属性数据类型/单位、已有关系谓词的有效版本进行校验；输出 `accepted | needs_review | rejected` 及机器可读的 `reason_codes`。不改变开放抽取层、不静默丢弃数据、不越过人工审核。
- **OR-02 端到端知识证据追踪**：统一 `trace_id` 与 `request_id`，把原始文档版本/页或时间戳、chunk、原文 quote、开放 statement、alignment、typed fact、rule derivation、retrieval hits、最终回答引用连接；区分 *extracted*, *inferred*, *generated*，并记录经过的知识版本和时间视图。
- **OR-03 细粒度知识访问策略**：在 KB 授权基础上支持按 `entity_type`、`relation_type`、`attribute`、`evidence`/安全分类及查询用途做读取过滤；跨 KB/跨租户不得联结。**同时防止通过计数、邻居数量、路径存在性、引用和错误响应泄露被拒绝节点**。审计 `allow/filter/deny/error` 的判定（不记录明文病历内容）。

### P1（有 P0 结果后实施）

- **OR-04 标准知识查询接口**：保留现有 REST 和 MCP；先定义有限、安全的 Triple Pattern + 有界 Path 查询契约，再评估是否以独立 adapter 提供 SPARQL 1.1 只读子集；禁止无界路径、更新查询、服务端联合查询，给超时、LIMIT、成本预算。
- **OR-05 可移植 Context Package**：扩展已有 RDF 导出，设计 manifest + schema/version + ontology + facts + evidence + temporal metadata + rule history + provenance + checksums（不自动包含原始敏感文档）；支持导出校验和离线试导入，不承诺首次即支持完整跨部署迁移。
- **OR-06 Guided Graph Retrieval**：按 seed 节点、边类型、类、时间窗口、named scope、安全上下文执行广度/深度可控的检索；证明路径带 source/valid_time/recorded_time；同时提供 `truncated` 和预算消耗。

### 不做（明确延后）

- 替换 KEE 的开源协议或上游历史；重新实现全套三元组数据库；引入消息队列/多微服务；通用复杂 OWL DL reasoner；把 SHACL-AF 当成全部 IAM；引入临床治疗自动决策；让模型直接执行治疗、修改病历或开立医嘱；未经验证地宣称信创合规或临床可用。

## 3. 目标架构与接口边界

```text
行业层：HCC-CIP / 工业 / 政企（行业知识包与行业规则不得反向依赖）
                |
            REST / MCP
                |
KEE Server：身份解析 → KB 角色/Token Scope → Policy Decision Point
                |                                  |
                |                  deny/filter + audit（所有读路径）
                v
查询层：Document Search / Semantic Query / Guided Graph Retrieval
                |
知识计算：Open Extraction → Alignment + Ontology Validation → Typed Ledger
                                |                         |
                           Human Review            Rules / Derivations
                |                                  |
         Provenance & Trace  <----------------------+
                |
     PostgreSQL + pgvector + Tantivy + Blob
```

**单一权限入口**：在 `kee-store::access` 的现有 KB 授权之后，统一调用 `PolicyDecisionPoint`，返回 `Allow | Filter | Deny`，`Error` 显式拒绝；直接 SQL 查询、RDF 导出、MCP、GraphRAG、图浏览器、聊天工具等均须审计，禁止以 URL 绕过。

**单一事实来源**：所有消费接口读取已有 typed/open/derived 账本；不得单独落一套“TrustGraph graph”造成真相分叉。

**策略顺序**：认证 → 资源作用域 → 有效 token 权限 → KB 角色 → 节点/关系/证据策略 → 最终数据读取 → 脱敏/审计。策略支持版本号和回滚；缺省策略兼容性需通过显式迁移配置确认：既有普通知识库遵循既有权限边界，新建敏感工作区缺省拒绝细粒度未授权数据。

## 4. 研发契约（逻辑协议，非已经存在的 API）

### 4.1 Alignment Validation

逻辑请求：`{kb_id, statement_id, candidate_type_id, candidate_relation_id, ontology_version, context_time}`。
逻辑响应：`{decision, reasons[], evidence_refs[], ontology_version, trace_id}`。

- `decision` = `accepted | needs_review | rejected`；`reason` 用稳定枚举：`DOMAIN_MISMATCH`、`RANGE_MISMATCH`、`DISJOINT_TYPE`、`DATATYPE_INVALID`、`UNIT_CONFLICT`、`ONTOLOGY_VERSION_STALE`、`EVIDENCE_MISSING`、`AMBIGUOUS_BINDING`。
- Domain/range 应考虑多父继承和当前本体版本；`needs_review` 不得自动物化为 typed fact；拒绝候选不删除源 open statement。
- 未知对象类型不得被误判为明确类型不匹配，应送 `needs_review` 并明确未知原因；不得把 LLM 置信度当唯一准入条件。
- 一次批量任务须有可恢复标识，重试幂等、关联同一 `statement_id + ontology_version + candidate`。

### 4.2 Query Authorization

逻辑输入：`{actor_id, token_scope, kb_id, action, purpose, resource_labels, time_context}`。
逻辑结果：`{effect: allow|filter|deny, policy_version, decision_id, reasons[]}`。

- 接口读取前逐个资源判断；`filter` 在响应、聚合、存在性测试、GraphRAG seed、citation、导出中都生效；不可仅在 UI 隐藏。
- 未授权请求返回现有约定的 `403` 或 `404`（防存在性泄漏），不在错误内容中附带受保护名称。
- 高敏数据执行明确用途与主体权限检查；任何 policy 解析失败都不能降级为允许。
- 测试矩阵覆盖：匿名、Viewer、Editor、Admin、系统管理员、只读 PAT、限定 KB PAT、过期/撤销 token，以及两个 KB/两个 workspace。

### 4.3 Trace & Provenance

建议 Trace 结构：`{trace_id, operation, actor_pseudonym, kb_id, as_of, valid_at, ontology_version, policy_version, nodes[], links[], output_refs[], truncated, created_at}`。节点类型为 `source_document_version | chunk | statement | binding | typed_fact | rule | derivation | retrieval | answer`。

- Trace ID 可供后端定位；**对用户返回的 trace 必须再次策略过滤**，不得因溯源而泄密。
- 证据定位需可读：文档版本、页码/文本位置、OCR bbox、音频起止毫秒（根据来源可用），保留 `origin=stated|ocr|transcribed|described`。
- 回答引用只允许指向调用者有权阅读的有效证据；不可把推理链中的生成段落伪装为原始证据。
- 对 `as_of` 查询记录有效时间与记录时间；政策历史追踪不代表允许读取历史上曾授权但当前无权查看的数据。

### 4.4 Guided Graph Query

逻辑输入：`{kb_id, seeds[], allowed_node_types[], allowed_predicates[], valid_at?, as_of?, max_hops<=4, max_nodes<=500, timeout_ms<=3000, user_context}`。阈值均为 **PoC 初始默认上限**，性能测试后可调整，不能视为已达成指标。

逻辑输出：`{nodes[], edges[], evidence_refs[], truncated, visited_count, trace_id}`，输出中的引用受同一策略控制。支持零结果但不能据此推断隐藏节点。先实现 API 级有限查询，再单独评估 SPARQL 兼容层，避免给现有 SQL 层添加不受控全图扫描。

### 4.5 Context Package v0.1

`manifest.json` 至少含 `format_version`、`origin_kb`、`ontology_version`、`exported_at`、`valid_time_policy`、`hashes`、`redaction_profile`；`ontology.ttl`、`graph.ttl`、`provenance.jsonl`、`policies.redacted.json`（可选）与校验和表。敏感原始材料默认不包含；仅在拥有显式授权且满足目的限制时输出。导入先跑 dry-run，形成差异报告和外部 IRI 映射，不默默合并实体。

## 5. 文件落点与预计变更（仅建议，非立即创建）

| 需求 | 主要现有目录 | 建议改动方式 |
| --- | --- | --- |
| OR-01 | `crates/kee-server/src/phrase_alignment.rs`、`type_alignment.rs`、`crates/kee-reason/src/ontology.rs` | 复用现有校验工具，增加独立 Validator；新测试覆盖未知/冲突/继承 |
| OR-02 | `crates/kee-ingest/src/provenance.rs`、`crates/kee-server/src/retrieval.rs`、`api/chat*.rs`、`crates/kee-store/src/audit.rs` | 先定义 Trace schema，再以已有证据 ID 贯通检索/问答；避免重新存原文 |
| OR-03 | `crates/kee-store/src/access.rs`、`crates/kee-server/src/api/{graph_routes,mcp,export_routes}.rs` | 在 KB 权限之后统一 PEP/PDP；增加针对侧信道的负向测试 |
| OR-04 | `crates/kee-server/src/rdf.rs`、`api/graph_routes.rs` | 提供只读 adapter 及受限查询能力，未经验证不得承诺全功能 SPARQL |
| OR-05 | `crates/kee-store/src/export.rs`、`crates/kee-server/src/rdf.rs` | 在现有 RDF 导出之上加 manifest / 检验 / dry-run |
| OR-06 | `crates/kee-server/src/retrieval.rs`、`crates/kee-search` | 增加时间/谓词/类型过滤与显式预算，不复制存储引擎 |
| 行业试点 | **独立** `examples` 或部署侧行业 pack | HCC 的医学本体、指南、规则与验证数据不进入通用 Crate |

**数据库策略**：先在现有表中定位 `fact_evidence`、`audit_events`、ontology 定义版本、历史规则和 KB 授权边界；只对确无已有载体的 `trace` 元信息、策略版本、审计判定等设计新增迁移。禁止以概念名称相似为由新建重复事实表。新增索引前必须解释执行计划与写入开销；迁移要求前滚、幂等/可恢复、备份演练。

## 6. 工作包、依赖与建议排期（30 天 / 4 周）

| ID | 时间窗 | 工作包 | 前置条件 | 输出及质量门槛 |
| --- | --- | --- | --- | --- |
| W0 | D1–D3 | 基线/许可证/上游与源码审计，明确已有-部分-未实现 | main 固定 SHA | 功能矩阵、可复现测试命令、benchmark 样本、架构 ADR 草案 |
| W1 | D4–D9 | OR-01：对齐约束及拒绝原因 | W0 | 单测 + E2E；所有被拒绝候选仍可追溯 open statement |
| W2 | D7–D14 | OR-02：统一 Evidence Trace | W0 / W1 schema | 来源 → 引句 → 事实 → 检索 → 回答可回溯，删除/撤回后无陈旧引用 |
| W3 | D10–D19 | OR-03：PDP/PEP 与安全策略 | W0；先授权测试 | 全部读取路径 fail-closed；跨 KB、导出、MCP、计数侧信道测试通过 |
| W4 | D17–D23 | OR-06：有界图谱查询 | W2 / W3 | 限深/限时/限节点可生效；过滤节点不出现在路径与来源 |
| W5 | D21–D26 | OR-04 / OR-05：标准查询/知识包 Spike | W2 / W3 | 独立 PoC、往返保真报告，不强制并入生产 |
| W6 | D26–D30 | 医疗行业应用验证/回归/发布评审 | W1–W5 | 非真实或脱敏授权数据验证报告、风险登记、决定是否进入 v0.2 release |

人力建议：后端 Rust/数据库 2 人、测试/安全 1 人、知识工程 1 人（可兼职），HCC 试点另需有资质的临床专家审核；实际工期须评审后确定。

## 7. 测试计划与量化验收（计划值，不是当前性能声明）

### 正确性

- **无数据损坏**：既有导入、抽取、人工审核、账本、反向撤销、历史查询和 RDF 导出回归 100% 通过。
- **本体规则**：手工构造含多继承、domain/range、互斥、数据类型、单位和未知类型的基准集；每条至少有清楚的接受/拒绝/人工审核 oracle；**硬约束违规误放行数为 0**。
- **证据正确性**：样本中事实/检索结果的证据 ID 均可解析为源文档版本与原句；不能解析的引用不作为可信引用返回；抽样有效证据定位正确率目标 ≥ 98%（数据集和分母需随报告公开）。
- **时间正确性**：包含事后补录、撤销、更正和不同记录时刻的黄金测试；不允许任何旧 `as_of` 查询被新知识提前污染。
- **知识包保真**：导出/试导入后 RDF IRI、语义角色、证据 ID 映射、时间区间不丢失；原始敏感文档的缺省导出数为 0。

### 安全

- 未授权节点、属性、证据或跨 KB 读取成功数 **0**，包含直接 API、图检索、GraphRAG、MCP、导出、聊天和聚合计数。
- 令牌收窄后的权限不得高于原主体；撤销 token 后立即拒绝新请求。
- 执行策略异常/超时/缺上下文时 fail closed；审计日志不包含明文受保护内容。
- 所有权限回归须在 CI 跑通；关键入口增加渗透测试用例和并发访问测试。

### 性能（基准测试目标，可根据硬件与样本修订）

- 同规格环境下，新增授权策略的正常单次 KB 读取 p95 延迟增量目标 < 20%；如果超过则需提供分析/优化方案，不可通过关闭策略来“达标”。
- 引导式图遍历初始默认 `max_hops=4, max_nodes=500, timeout_ms=3000`；超限返回安全的 `truncated` 或超时，不得卡死服务。
- 至少在 1 万、10 万、100 万条事实三个规模运行分层压测；公布硬件、并发数、数据分布、数据预热、p50/p95/p99、错误率和资源占用。**没有实测结果前不宣称可支持特定规模**。

### 医疗试点安全门槛

- 仅用于医疗知识检索、指南证据展示、非生产临床路径候选解释；**绝不作为自主诊疗/开药决策**。
- 建立指南版本、发布日期、适用人群、证据等级、反例、禁忌、过期处理、临床审核与偏差记录；不使用未经授权的患者真实数据。
- 先做专家评测与本地部署/隐私影响评估，再讨论与医院业务系统联动。

## 8. 版本治理、向后兼容与回滚

- 所有 schema/API 的更改须提供差异表：`旧字段 → 新字段 → 默认行为 → 迁移方式 → 废弃时间`。
- 既有 REST/MCP JSON 字段、RDF 导出与 `urn:kee:...` 标识保持稳定；新增字段须可选，旧客户端可忽略。
- 审批策略版本在同一事务或可追溯工作流中发布；策略失效可回退到**上一已批准、仍安全**的策略，不可回退为全开放。
- 采用 feature flag：`alignment_validation_v2`、`evidence_trace_v2`、`fine_grained_policy_v2`、`guided_graph_query_v2`（建议名称，待统一配置规范）；逐 KB 或逐 workspace 灰度，记录对照测试。
- 迁移前备份、迁移后核验与恢复演练；不假定数据库 schema 可以自动降级。对于危险新功能优先提供“关闭新入口 + 保留持久化数据”的应用级恢复方案。

## 9. 文档、审查和交付 Definition of Done

每个工作包需提交：

1. **ADR/设计变更记录**：说明为什么沿用或改变现有 `docs/design/*` 契约，引用对应历史决策；未经评审不得把未来状态写进当前设计文档。
2. **公开接口契约**：输入/输出、鉴权、错误码、幂等、版本化、时间语义、策略执行点；REST/MCP/SDK 统一。
3. **迁移与兼容方案**：精确迁移文件、受影响表、索引代价、旧客户端影响、备份与恢复步骤。
4. **自动化证据**：单测/E2E/回归/安全/压测脚本及运行日志，报告用例数与失败列表。
5. **运维手册**：本地部署、性能指标、审计保留、数据清理、备份演练、告警和故障降级。
6. **业务验收**：由产品和医疗试点负责人签字确认知识查询的证据准确性、隐私和人工审核边界。

**发布闸口**：P0 需求全部通过与已有功能的回归测试、授权负向测试及数据迁移演练；未完成 P1 不应阻塞仅含 P0 的里程碑，但不得宣传未实现能力。

## 10. 建议的首批研发 Issue

- `OR-00`：基线 E2E、上游许可证和设计决策差距审计。
- `OR-01`：开放语句对齐校验协议、拒绝原因、人工审核联动。
- `OR-02`：贯穿 extraction → retrieval → answer 的可信证据 Trace。
- `OR-03`：KB RBAC 后的资源级 PEP/PDP + 跨 KB 安全矩阵。
- `OR-04`：可限制成本的图谱查询 API、截断和时态过滤。
- `OR-05`：RDF/PROV-O + Context Package v0.1 往返验证。
- `OR-06`：HCC 示例本体和公开/合成指南数据的专家审核测试集。

## 11. 参照与基线资料

- 本仓库：`KEE/docs/design/{ontology,extraction,ledger,rules,access-and-audit,chat-and-mcp}.md`
- 现有决策：`KEE/docs/decisions/{0012,0019,0020,0040,0044,0046,0062}-*.md`（根据现存文件名核对）
- TrustGraph：[README](https://github.com/trustgraph-ai/trustgraph/blob/master/README.md)；其 RDF/OWL/SHACL/PROV-O/GraphRAG 架构供对标，不表示 KEE 已实现同等能力。
- 标准：W3C RDF 1.1、OWL 2、PROV-O、SHACL、SPARQL 1.1；按各自标准范围逐项验证，不以单一库的实现替代规范。

---

**维护规则**：本文件是 V0.2 **规划快照**，不是当前实现真源。实施落地后，由对应 PR 更新 `KEE/docs/design/` 的“当前事实”，必要时新增按序号排列的 ADR；不得直接重写旧 ADR 的历史动机。
