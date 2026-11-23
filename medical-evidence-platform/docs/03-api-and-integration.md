# KEE Medical V1.0 服务接口与集成规范

> 文档编号：MKE-API-03
> 版本：1.0.0
> 状态：接口设计基线（待评审；非代码实现）

## 1. 设计原则

- 所有对外接口采用版本化 API 路径，首期建议 `/api/v1`。
- FastAPI 医疗服务对外提供领域接口；KEE Adapter 隔离 Rust 引擎接口。
- 前端不直接访问数据库或 KEE 内部服务。
- 所有接口执行身份认证、租户授权、资源范围校验和审计。
- 长耗时采集、解析、抽取、批量映射和索引构建采用异步任务模式。
- 写操作支持幂等键或可识别的请求 ID；重复提交不得生成重复资产或重复发布。
- 接口契约以 OpenAPI 为准，重大变更需版本兼容策略。

## 2. API 资源分组

| 分组 | 建议路径 | 主要能力 |
|---|---|---|
| Knowledge Sources | `/api/v1/sources` | 来源注册、连接测试、启停、健康状态 |
| Documents | `/api/v1/documents` | 文档登记、版本、分类、元数据 |
| Assets | `/api/v1/assets` | 多模态资产上传、元数据、版本 |
| Ingestion | `/api/v1/ingestion/jobs` | 采集任务创建、查询、重试、取消 |
| Extraction | `/api/v1/extraction/jobs` | 解析和知识抽取任务 |
| Content | `/api/v1/content-blocks` | 页、段、表格、区域和时间片定位 |
| Entities | `/api/v1/entities` | 医学实体查询、创建、维护 |
| Concepts | `/api/v1/concepts` | 标准术语和编码查询 |
| Terminology | `/api/v1/terminology/mappings` | 术语映射候选、确认、撤销 |
| Relations | `/api/v1/relations` | 关系定义和实体关联 |
| Assertions | `/api/v1/assertions` | 知识主张创建、查询、版本 |
| Evidence | `/api/v1/evidence` | 证据定位、支持/反驳关联 |
| Ontology | `/api/v1/ontology/packages` | 本体包、版本、类、属性和校验 |
| Conflicts | `/api/v1/conflicts` | 冲突列表、对比、处置 |
| Reviews | `/api/v1/reviews` | 审核任务、决定、审批轨迹 |
| Rules | `/api/v1/rules` | 规则集、规则版本、测试和发布 |
| Annotation | `/api/v1/annotation-guidelines` | 标注规范、关系标签、质检规则 |
| Search | `/api/v1/search` | 关键词、语义、混合、跨模态检索 |
| Graph | `/api/v1/graph/query` | 子图、路径和受控推理查询 |
| Knowledge Ask | `/api/v1/knowledge/ask` | 带证据引用的 RAG 问答 |
| Audit | `/api/v1/audit-events` | 授权范围内的审计查询 |
| Integration | `/api/v1/integrations` | 外部客户端、订阅、投递状态 |

以上为资源规划，最终请求/响应字段需由领域契约文档和 OpenAPI 定义。

## 3. 统一请求与响应约定

建议所有响应携带：
- request_id：请求唯一标识。
- trace_id：跨服务链路标识。
- data：业务结果。
- error：标准错误对象（仅失败时）。
- pagination：分页信息（列表接口）。

错误对象至少包含 code、message、details、retryable。不得在错误详情中泄露访问令牌、患者隐私或内部密钥。

分页接口需限制最大 page_size；排序字段必须白名单化。过滤条件必须在租户和授权范围内执行。

## 4. 异步任务约定

采集、文档解析、OCR、转写、知识抽取、批量术语映射、冲突扫描和索引构建建议采用统一任务资源。

任务状态建议：queued、running、succeeded、partially_succeeded、failed、cancel_requested、cancelled。

任务记录需包含：
- task_id、task_type、tenant_id、initiator、input_refs；
- parser/model/rule version；
- progress、created_at、started_at、finished_at；
- result_summary、error_code、retry_count；
- correlation_id 和审计关联。

任务必须支持幂等、超时、有限重试、失败原因记录和人工重跑。重跑应产生新的执行记录或明确的 attempt 版本，不覆盖历史结果。

## 5. KEE Adapter 契约

Adapter 至少提供以下抽象能力：

| Adapter 能力 | 输入 | 输出/结果 |
|---|---|---|
| upsert_entity | 医学实体及标识映射 | KEE 实体引用 |
| upsert_relation | 关系谓词和端点 | KEE 关系引用 |
| publish_assertion | 主张、限定条件、时态、来源 | 知识写入结果 |
| attach_evidence | 主张引用和证据定位 | 证据关联结果 |
| sync_ontology | 本体包及版本 | 导入/校验结果 |
| resolve_entity | 实体候选和上下文 | 消歧候选及解释 |
| detect_conflicts | 新主张或扫描范围 | 冲突候选列表 |
| query_graph | 受限查询条件 | 子图/路径 |
| hybrid_search | 查询、过滤器和权限上下文 | 排序结果及引用 |
| retract_or_supersede | 目标引用和原因 | 撤回/替代结果 |

该表是领域适配接口建议，不保证现有 KEE 已有同名 API。开发前须逐项对照 Rust crates、服务路由和实际请求/响应进行能力盘点。

## 6. 统一检索约定

检索请求需包含 query、search_modes、knowledge_types、disease/domain filters、source/version filters、effective_at（可选）、tenant/scope context、top_k。

检索结果至少返回：
- assertion/entity/document 标识；
- 匹配片段和来源；
- 来源版本及发布时间；
- evidence locator；
- 知识审核/发布状态；
- 适用范围和时间；
- 检索通道及相关性分数（若可提供）。

未经授权或未发布的知识不得因向量相似度高而泄露给调用者。召回分数不是医学证据等级。

## 7. RAG 输出约定

知识问答结果应区分：
1. 检索到的已发布知识。
2. 证据来源与定位。
3. 模型生成的归纳内容。
4. 不确定、冲突或缺失信息。
5. 适用范围和版本提示。

若无足够证据，应返回证据不足，不得编造指南出处。RAG 不得将模型生成文本伪装成原始指南结论。临床应用需经过独立风险评估和批准。

## 8. 外部平台集成

### 8.1 高质量数据集加工生产平台

提供：
- 自由文本术语标准化；
- 实体和关系标注规则查询；
- 任务适用的医学知识检索；
- 标注结果医学逻辑校验；
- 数据集质量问题及证据返回；
- 知识规则版本和生效状态查询。

集成时必须传递数据集项目、标注任务、规则版本和授权范围，以便结果可复现。

### 8.2 资源与数据一体化调度管控平台

提供/获取：
- CPU/GPU/存储资源申请与任务状态；
- 数据目录和元数据；
- 可用计算资源、配额和任务约束；
- 知识处理任务的资源需求与运行状态。

资源调度接口不得向知识服务泄露不必要的患者明细数据。

### 8.3 上层临床、科研与运营系统

通过统一 Open API 提供知识检索、规则查询、图谱路径、语义映射和知识问答。每个调用方必须独立注册、授权、限流、审计和撤销。

## 9. API 生命周期

API 生命周期：设计 → 契约评审 → 实现 → 自动化契约测试 → 测试环境发布 → 调用方验证 → 正式发布 → 监控 → 版本弃用 → 下线。

破坏性变更必须升级主版本或提供兼容窗口。API 变更需更新 OpenAPI、示例、错误码、权限说明和调用方通知。

## 10. 集成可靠性

- 网络超时、指数退避和有限重试。
- 幂等键与去重策略。
- 事务发件箱或可靠事件投递。
- 失败队列和人工补偿流程。
- 版本通知可重复投递，消费端按事件 ID 幂等处理。
- 所有跨服务操作带 trace_id。
- 重要写入记录审计事件。
