# KEE Medical V1.0 领域模型与数据设计

> 文档编号：MKE-DATA-02
> 版本：1.0.0
> 状态：逻辑模型设计（待评审；非数据库迁移脚本）

## 1. 设计原则

1. 原始来源、原始资产、解析结果、医学实体、知识主张、证据和审核记录分层保存。
2. Entity、Relation、Assertion 和 Evidence 是不同语义对象，不合并为单一知识表。
3. 所有正式知识保留来源版本、证据定位、抽取批次、模型/规则版本和治理状态。
4. 支持租户边界和知识空间边界。
5. 支持双时态查询：业务有效时间与系统记录时间分离。
6. 标准术语映射必须标明映射关系类型和来源，不能将近似匹配当作等价。
7. 逻辑模型先于物理表结构；最终字段、索引、约束和分区方案须经现有数据库审查后确定。

## 2. 核心领域对象

### 2.1 Source（知识来源）

描述一个可接入或已接入的知识源。

建议属性：source_id、tenant_id/共享范围、source_type、name、publisher、authority_class、license/permission_reference、connection_profile_ref、sync_policy、health_status、created_at、updated_at。

连接凭据必须引用密钥管理系统中的密钥，不得明文保存或写入审计日志。

### 2.2 Document / Asset（文档与多模态资产）

Document 表示具有标题、发布者、文档类型和版本的知识文献；Asset 表示实际文件或媒体对象。一个 Document 可关联多个 Asset，一个 Asset 可派生多个处理版本。

建议元数据：asset_id、document_id、modality、mime_type、storage_key、sha256、size_bytes、source_version、ingested_at、security_label、retention_policy。

### 2.3 Content Block（内容块）

表示解析后可定位的内容单元，例如页面、章节、段落、表格、图像区域、音频片段或视频片段。

定位信息需支持：
- PDF/文档：页码、章节路径、段落/块编号、字符区间。
- 表格：页码、表号、行列坐标。
- 图像：资产版本、坐标系、区域边界。
- 音视频：起止时间戳。
- DICOM：Study/Series/Instance 等受控标识和帧/区域定位；具体规范单独制定。

### 2.4 Entity（医学实体）

代表经过规范化的医学对象，例如疾病、症状、药品、检查、检验项目、手术、解剖部位、微生物、基因/蛋白。

建议属性：entity_id、tenant/scope、entity_type、canonical_label、language、definition、lifecycle_status、created_at、updated_at。

实体别名独立管理，保留语言、缩写、来源和有效状态。实体不是某一份文档中的字符串提及。

### 2.5 Concept（标准术语概念）

代表外部标准体系中的概念。建议属性：concept_id、system_uri、system_name、system_version、code、display、language、status。

Entity 与 Concept 通过映射对象关联。映射类型至少区分 exact、broader、narrower、related、unmapped；并保存置信度、映射方法、来源、审核状态和版本。

### 2.6 Relation（实体关系）

表示两个实体之间的关系定义或关系实例。必须明确谓词、方向、语义类型和适用约束。

示例谓词：表现为、用于诊断、用于监测、治疗药物、禁忌药物、适应症、并发、组成、分级。关系不能只依赖自然语言标签，需有稳定 predicate code 和本体定义。

### 2.7 Assertion（知识主张）

Assertion 表示一条带上下文的医学主张，而不是简单的图边。它可表达主体、谓词、客体、限定条件、适用人群、临床场景、否定/不确定性、时间范围和状态。

建议逻辑属性：
- assertion_id、subject_entity_id、predicate_code、object_entity_id/value。
- qualifiers：人群、疾病阶段、治疗线次、剂量条件、检验方法、地域/机构等限定。
- polarity：支持/否定/不确定等语义。
- confidence：模型或规则给出的技术置信信息，不等同于循证等级。
- provenance：来源版本、抽取任务、模型版本。
- governance_status：candidate、pending_review、approved、published、rejected、superseded、withdrawn。

同一对实体可存在多条不同来源、不同时间、不同适用条件的 Assertion。

### 2.8 Evidence（证据）

Evidence 是支持、反驳或限定 Assertion 的来源证据。建议包含 evidence_id、source_id、source_version_id、asset_version_id、content_block_id、locator、excerpt、support_type、captured_at、integrity_hash。

证据摘录应遵循授权和版权要求；不应将付费数据库全文复制到无授权存储。

### 2.9 Ontology（本体）

本体包具有独立版本，包含 Class、Object Property、Data Property、约束、术语映射和导入来源。发布版本不可被原位覆盖；变更生成新版本，并记录兼容性及下游影响。

### 2.10 Rule（规则）

规则对象包含 rule_id、rule_type、expression/decision_model、input_schema、output_schema、scope、source_evidence、version、effective_period、test_cases、approval_state、enabled_state。

规则表达式必须定义执行语义、单位、缺失值行为、边界条件、优先级和错误处理。

### 2.11 Review / Audit（审核与审计）

审核任务必须绑定被审核对象的具体版本快照，防止审核期间对象发生变化。审核决定记录审核人、角色、决定、理由、时间和所审版本。审计事件记录主体、动作、对象、租户、时间、请求关联 ID、结果和必要的变更摘要。

## 3. 逻辑数据库 Schema 建议

以下为逻辑分区建议，不代表已经创建物理 Schema 或表。

| Schema | 逻辑实体 | 职责 |
|---|---|---|
| iam | tenants、users、roles、permissions、memberships | 身份、租户与授权 |
| source | sources、source_sync_runs、documents、document_versions | 知识来源与文献版本 |
| asset | assets、asset_versions、media_objects | 原始和派生文件 |
| extract | extraction_jobs、parsers、content_blocks、mentions | 解析和抽取运行 |
| medical | entities、entity_aliases、concepts、entity_concepts、relations、assertions | 医学语义资产 |
| evidence | evidence_items、evidence_links | 证据和主张关联 |
| ontology | packages、versions、classes、properties、mappings | 本体定义和映射 |
| governance | conflicts、review_tasks、review_decisions、publication_records | 冲突与审核治理 |
| rules | rule_sets、rules、rule_versions、rule_tests | 临床规则 |
| annotation | guideline_sets、guidelines、label_types、relation_labels、quality_checks | 标注规范 |
| semantic | embedding_profiles、index_jobs、index_refs | 语义索引元数据 |
| integration | api_clients、subscriptions、delivery_jobs | 外部服务集成 |
| audit | audit_events、security_events | 审计与安全事件 |

## 4. 双时态与版本

双时态至少区分：

- **Valid Time**：主张在其医学/业务语境中适用的时间区间。
- **Transaction Time**：平台何时记录该主张、何时将该记录替换或关闭。

建议字段语义：
- valid_from、valid_to：适用区间。
- recorded_from、recorded_to：系统记录区间。
- source_published_at：来源发布时间。
- source_effective_at：来源声明的生效时间。
- source_version_id：来源版本。
- supersedes_assertion_id：被替代主张（如适用）。

时间字段不得互相混用。未知时间应显式为空或标注 unknown，不得伪造日期。所有时间统一存储 UTC，展示时按用户/机构时区转换。

## 5. 证据链

建议链路：

`Source → Document Version → Asset Version → Content Block/Locator → Extraction Run → Entity Mention/Assertion → Evidence Link → Review Decision → Publication Record`

必须能从已发布 Assertion 反查：
- 来源机构和来源版本；
- 原文定位（页、段、表、图像区域或媒体时间戳）；
- 抽取工具、模型和提示/规则版本；
- 术语映射记录；
- 冲突处理记录；
- 审核人、审核结论和发布时间。

## 6. 多租户和知识空间

建议将资源可见性建模为租户、知识空间和共享范围的组合：
- 平台级公共知识；
- 医院级知识；
- 科室级知识；
- 个人知识；
- 项目/科研空间。

跨空间共享必须显式授权并记录审批。患者数据与公共医学知识应采用不同资源域和访问策略。数据库行级安全可作为纵深防御，不替代服务端授权。

## 7. 索引与检索数据

- 原始文件存对象存储。
- 业务元数据和工作流状态存关系数据库。
- 图谱、全文和向量索引优先评估 KEE 当前能力。
- 每个索引记录关联内容版本、embedding profile、模型版本、索引构建时间和状态。
- 索引可重建，不作为唯一事实来源。
- 删除或撤回知识时，必须同步处理缓存和索引，并有完成状态记录。

## 8. 关键约束与一致性要求

1. 已发布知识不得无痕原位覆盖。
2. Evidence 必须能定位到不可混淆的来源版本。
3. Assertion 发布前必须满足其配置的审核策略。
4. 映射关系必须区分等价、上下位和相关关系。
5. 规则版本发布前必须通过结构校验和测试用例。
6. 删除采用受控撤回/归档策略，审计记录不得因业务对象删除而消失。
7. 租户隔离测试覆盖查询、搜索、导出、图谱遍历、缓存和 API。
8. 物理表、字段、索引、唯一约束和分区策略在代码审查后另行形成数据库详细设计及迁移计划。

## 9. 示例知识主张（仅用于说明结构）

```json
{
  "schema_version": "1.0.0",
  "assertion_id": "assertion-example-001",
  "subject": {"entity_id": "entity-example-disease"},
  "predicate": {"code": "evaluated_by"},
  "object": {"entity_id": "entity-example-test"},
  "qualifiers": {
    "population": null,
    "clinical_context": null,
    "conditions": []
  },
  "evidence_links": [
    {
      "source_version_id": "source-version-example",
      "locator": {"page": 12, "anchor_id": "anchor-example"}
    }
  ],
  "temporal": {
    "valid_from": null,
    "valid_to": null,
    "recorded_from": "2026-01-01T00:00:00Z",
    "recorded_to": null
  },
  "governance_status": "pending_review"
}
```

该示例是结构占位，不表达任何真实临床推荐。
