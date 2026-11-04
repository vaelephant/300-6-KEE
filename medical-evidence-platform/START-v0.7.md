# V0.7 OCR 人工审核与检索生效

本版在原页旁增加确认、纠正、驳回和历史记录。原始OCR文字不修改；新增review revision记录，检索使用最新审核状态。未构建独立批量审核队列，当前入口为检索命中区域。

## 升级启动

沿用原DATABASE_URL及已有数据库：

```bash
cd medical-evidence-platform/back
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m alembic upgrade head
python3 -m app.demo
export EVIDENCE_PRINCIPALS_JSON='{"local-demo-token":{"tenant_id":"hospital_demo","actor_id":"developer","patients":["patient_demo"],"permissions":["read","ingest","review"]}}'
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

注意新增独立review权限。旧凭证仅有read/ingest时不能提交审核，返回403。请勿默认给所有导入用户审核权。示例仅供本地合成数据。

另一个终端执行front目录的npm ci、npm run dev。访问http://127.0.0.1:3000。

## 操作步骤

1. 导入06-scanned-report.pdf并执行英文OCR（安装说明见START-v0.6.md）。
2. 搜索Creatinine，点击打开原页定位。
3. 右侧输入审核说明，可确认原始文字、编辑并保存纠正或驳回。
4. 审核后重新检索；纠正使用新文字匹配，原始OCR仍显示供核对。
5. 默认排除驳回区域；勾选“包含驳回”可找回并重新审核。
6. “仅已确认/纠正”只显示已审核OCR，普通PDF文字当前没有审核接口，因此也不会出现在该过滤结果中。

确认原始文字意味着恢复原始识别文本。如需维持纠正文字，请选择“保存纠正”，不要误点确认原始文字。驳回后用于历史检索的是原始OCR文字；旧纠正内容保留在审核历史中。

## 模型与接口

0006迁移增加ocr_reviews，按tenant_id+anchor_id+revision唯一，保存review_id、decision、reviewed_text、actor_id、时间、说明。接口只追加记录，不覆盖历史；尚无数据库层防篡改触发器或签名。

POST /v1/documents/reviews：anchor_id、expected_revision、decision（confirmed/corrected/rejected）、text、reason。服务端读取身份与患者授权；客户端不能自报审核人。修订号过期或并发冲突返回409。

GET /v1/documents/reviews/{anchor_id}：按当前read权限返回历史，最新在前。

POST /v1/documents/search 增加reviewed_only、include_rejected；返回original_text、有效text、review_revision和review_status。仍然是关键词检索，不是语义诊断或全量证据覆盖证明。

## 验证

21项后端测试通过，新增覆盖纠正后新词可查/旧词不再匹配、驳回默认隐藏、再次确认、历史三版、过期修订号拒绝和无review权限拒绝。前端生产构建和SQLite迁移升级通过。未进行PostgreSQL实机验证、并发负载测试或浏览器视觉回归。

## 边界

- 本版审核是单个OCR区域文字核对，不等同于医生签署报告、确认诊断或整份文档已审核。
- 文档总状态仍显示OCR完成/未审核；逐区域状态以搜索结果和审核历史为准，尚未汇总全部区域审核进度。
- 查询为开发实现，按患者逐条检查最新审核及文字匹配，尚未建立审核投影索引；大文档量需改为索引更新/数据库查询优化。
- 没有自动回填临床事实或更改既往问答；原版本证据包未集成审核影响提示，后续扩展血缘影响服务。
- 继承V0.6的同步OCR和生产权限限制。中文语言包和效果仍待专项验证。
