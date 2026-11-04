# 医疗多模态证据平台 · 数据契约 V1.0.0

日期：2026-10-01。状态：开发基线提案，可用于下一轮建表和接口开发；尚未接入医院真实数据或形成生产验收结论。

## 1. 交付内容

schemas/ 提供 JSON Schema Draft 2020-12；examples/ 提供完全虚构的关联示例；tests/validate.py 提供结构和示例关联验证。安装 jsonschema[format]>=4.18,<5 后执行 python tests/validate.py。正式工程应锁定验证器及其传递依赖版本。

五类核心契约为 asset-version、evidence-anchor、clinical-fact、query-definition、evidence-bundle；另提供 query-request。所有根对象禁止额外字段。参数 Schema 本身允许标准 JSON Schema 结构，注册时必须再验证其合法性并限制复杂度。所有外部 $ref 仅从受控本地注册表解析，禁止运行时任意联网加载。

## 2. 实体职责与关联

| 契约 | 责任 | 主标识与关系 |
|---|---|---|
| AssetVersion | 保存一个患者范围内原始资产的确定版本 | asset_version_id；asset_id+version 唯一 |
| EvidenceAnchor | 在确定资产版本中定位证据 | anchor_id → asset_version_id |
| ClinicalFact | 保存临床语义、值、时间、处理来源和发布状态 | fact_version_id；anchor_ids → 来源锚点 |
| QueryDefinition | 注册经评审的查询、语义口径与执行产物 | query_id+version；绑定产物哈希、权限与测试 |
| EvidenceBundle | 固化本次查询的事实、证据、覆盖范围及问题 | bundle_id → query_run_id、snapshot_id、查询版本 |
| QueryRequest | 调用方请求某个已注册查询 | 查询版本、患者范围、参数、截至时间 |

关系：证据包 → 事实版本 → 来源锚点 → 资产版本。派生事实另外保存输入事实版本及处理运行标识。相同内容并不意味着相同患者或相同临床事件，禁止仅凭哈希跨患者合并。

## 3. 通用约定

- schema_version 表示契约结构版本，version 表示业务对象版本，两者分开。破坏兼容的结构修改升主版本；严格客户端也需同步升级，不能假定增加字段自动兼容。
- ID 是不透明字符串，生产由服务端生成，不使用姓名、身份证号作 ID。tenant_id 为服务端归属信息，不能相信客户端自报租户。
- 请求中的 patient_id 和 encounter_id 只是目标选择，不代表授权。服务端必须用认证身份、用途、授权范围校验；as_of 不能恢复已经撤销的权限。
- 时间有 datetime/date/unknown 三类；datetime 必须有时区，date 保留原始日精度。event_time 为发生时间，recorded_time 为源记录时间，ingested_at 为平台获知时间。
- 数值使用十进制字符串，避免二进制浮点误差；原始值、比较符和单位同时保留。小于5不能解释为精确的5。原始单位不明时保留原文并隔离，不能随意填标准单位。
- 模型自报置信度不作为真实性概率；派生说明与源事实分开。模型推断必须以 origin=model_inference 标识。
- encounter_id 为 null 表示尚未关联明确就诊，不表示整个患者范围已经完整。

## 4. 多模态范围

当前锚点支持字段、Unicode字符区间、PDF归一化页面区域、DICOM实例帧以及音视频时间片段。文本区间为左闭右开；页面和帧从1开始；媒体时间为毫秒左闭右开。页面坐标原点为左上角，x/y/width/height 在0至1之间。

字符区间必须指向固定的文本表示版本，不能对规范化后的文字使用原文偏移。PDF区域指向确定渲染表示及页号。DICOM 当前支持实例/帧定位，不承诺三维病灶坐标和分割模型；影像ROI及视频区域可在后续契约中扩展。支持锚点类型不等于已实现对应解析器。

本版资产限定单患者范围；批量CSV等先建立导入批次，再拆为患者级记录资产。保留原始批次关系需要后续 ingestion_batch 表；不能将整个多患者文件作为可直接调阅的患者证据。

## 5. 状态与版本规则

- 资产和事实版本内容不可静默覆盖；更正生成新版本并引用 supersedes。仅首次版本允许没有前序，迁移快照例外须留审计。
- publication_status：draft → published 或 quarantined；隔离结果复核后发布新版本。withdrawn 表示不再默认提供。记录状态 final/corrected/cancelled 与发布状态分别处理。
- clinical_fact schema 支持诊断、用药等类型的基本容器；第一期实施和严验以 observation 为准。用药剂量、途径等专用契约后续细化，不能把通用文本容器当作完整用药模型。
- query lifecycle：draft → reviewed → published → retired。published 必须有审核和测试记录；执行代码与哈希必须存在并匹配。示例查询为 draft，执行文件、哈希和测试 ID 为占位，不能直接用于线上执行。
- execution_status 区分 completed/partial/failed；evidence_status 区分 supported/insufficient/conflicting/not_evaluated。completed 仅表示执行完成；示例只有一次检验，故证据不足以比较两次变化。
- supported 指支持本次定义的查询结果，不代表支持任何诊断推断。冲突、覆盖不足与错误以结构化列表保留。
- 证据包是当次快照，不覆盖历史内容。权限变化和来源更正的实时提示由外部状态表维护，读取时结合当前授权。

## 6. Schema 之外必须实施的业务约束

JSON Schema 不能替代关系、权限与临床规则校验。以下必须由服务端和数据库承担：

1. 所有引用存在，租户一致，患者和就诊归属相容；复合外键/查询过滤不允许跨租户关联。
2. 发布事实必须有有效锚点；证据包中的全部事实锚点必须可解析，evidence_id 不重复，引用不能指向其他患者。
3. text.end > start；media.end_ms > start_ms 且不超文件长度；x+width、y+height ≤1；页码/帧数不越界。
4. 日期时间验证器必须启用 FormatChecker；数据库保留源时区/精度语义。患者事实的事件时间早于入库可以正常存在，不做错误的统一时间排序限制。
5. 数量型检验必须检查指标、标本、单位、方法和记录状态。第一期查询只选择经过发布且有效的正式或修订结果；cancelled 排除。
6. event_state 与事实类型、来源一致；家族史不得变为患者本人确诊；医嘱开立不等同已给药。
7. 计算事实输入存在，全部源锚点可追溯，派生关系无环；程序版本、公式及输入版本不可缺失。
8. supersedes 指向同一业务实体的先前版本，禁止环和自引用；版本号唯一。源系统无版本时仅声称本平台快照版本。
9. 查询参数按注册 parameter_schema 二次校验；当前用户有 required_permissions；只允许 published 查询且产物校验通过。
10. 查询快照固定数据水位和查询版本；分页游标绑定快照及授权范围。撤权后旧游标和原文访问仍拒绝。
11. failed 不得伪装 supported；conflicting 必须有冲突项；calculation 输出及输入事实必须在可核验范围内。部分失败要返回 issues。
12. 原文访问句柄临时签发并再次授权，契约中不保存长期公开 URL 或密钥。

## 7. 数据库映射初版

建议 PostgreSQL；下表是逻辑映射，不是已执行的迁移SQL。

| 表 | 主键/唯一约束 | 关联与索引 |
|---|---|---|
| assets | (tenant_id, asset_id) | patient_id、encounter_id |
| asset_versions | (tenant_id, asset_version_id)；unique(tenant_id,asset_id,version) | 资产外键；源系统+主键索引 |
| evidence_anchors | (tenant_id,anchor_id) | 资产版本复合外键；locator JSONB |
| clinical_facts | (tenant_id,fact_id) | 患者、类型 |
| fact_versions | (tenant_id,fact_version_id)；unique(tenant_id,fact_id,version) | 患者+概念+事件时间+状态索引 |
| fact_evidence | (tenant_id,fact_version_id,anchor_id) | 两侧复合外键 |
| processing_runs | (tenant_id,processing_run_id) | 处理器、版本、参数与运行审计 |
| fact_dependencies | (tenant_id,output_version_id,input_version_id) | 两侧事实版本外键；防环校验 |
| query_definitions | (tenant_id,query_id,version) | 状态、定义JSONB、产物哈希 |
| query_runs | (tenant_id,query_run_id) | 身份、用途、参数、状态、快照ID |
| evidence_bundles | (tenant_id,bundle_id) | query_run_id外键、快照JSONB、创建时间 |

事实payload与数值明细可存JSONB起步，但患者、概念、时间、状态需投影为有类型的查询列并保持一致。数值使用NUMERIC，字符串原值另外保留。内容哈希校验原始字节，不对不同JSON序列化结果假定哈希一致。

双时态查询需要有效事件时间和平台版本生效区间。版本切换使用事务更新当前版本指针或有效区间，不能仅按 version 最大值处理撤销与历史快照。权限、审计、outbox及源同步水位表为独立基础模块，未在五类契约中混入。

## 8. 首个查询定义

creatinine_latest_two：按采样时间倒序返回同患者授权范围内两次有效血清肌酐。采样时间不明不擅自用报告时间替代；需显式规则或返回缺失。相同时间按稳定源标识排序，重复记录按源业务键及版本去重。不足两次返回已有记录及 INSUFFICIENT_OBSERVATIONS；不同单位/方法不可比时可展示原值但不计算差值。

测试分为：正常两次、仅一次、修订报告、撤销报告、权限拒绝、时间缺失、单位不明。当前示例展示仅一次这一场景；测试脚本验证的是契约，不代表查询执行功能已经实现。

## 9. 后续实现入口

依次实现数据库迁移与仓储、结构化接入映射、证据锚点解析、查询注册发布、参数化执行和证据组装。前端可基于 examples 并行实现事实列表与来源面板。
