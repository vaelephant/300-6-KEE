# V0.2：检验接入、查询与证据 API

在 V0.1 上增加第13张 source_records 表、0002迁移、FastAPI应用、合成身份初始化及端到端测试。本版为受控开发示例，不用于生产患者数据。

## 启动

```bash
cd back
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m alembic upgrade head
python3 -m app.demo
export EVIDENCE_PRINCIPALS_JSON='{"local-demo-token":{"tenant_id":"hospital_demo","actor_id":"developer","patients":["patient_demo"],"permissions":["read","ingest"]}}'
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

打开 http://127.0.0.1:8000/docs，在 Authorize 中填写 local-demo-token。示例凭证仅限本地开发。未配置凭证时所有业务接口拒绝访问。

```bash
curl -X POST http://127.0.0.1:8000/v1/ingestion/lab-records \
  -H 'Authorization: Bearer local-demo-token' \
  -H 'Content-Type: application/json' --data-binary @demo-ingest.json
curl -X POST http://127.0.0.1:8000/v1/queries/creatinine-latest-two \
  -H 'Authorization: Bearer local-demo-token' \
  -H 'Content-Type: application/json' -d '{"patient_id":"patient_demo"}'
curl http://127.0.0.1:8000/v1/evidence/anchor_1 \
  -H 'Authorization: Bearer local-demo-token'
python3 -m pytest -q
```

## 实现行为

- 接收已标准化的资产、锚点、事实和原记录；只支持配置中的 local_demo/CREA 血清肌酐演示。不是医院LIS通用连接器。
- 原始JSON按UTF-8、排序键及紧凑分隔符序列化，重算哈希和字节数，保存在数据库。哈希证明所保存字节一致，不证明外部来源真实性。
- 原字段值与事实原值核对；数值仅支持无换算精确结果。采样时间及单位等其他临床字段暂依赖接入方，下一阶段补齐完整源字段映射验证。
- 整批在事务中写入；同版本同内容返回unchanged，同ID内容改变拒绝。
- 同事实先取最新版本，再判断撤销/发布状态；因此撤销后不会回退到旧的正式报告。
- 查询以采样时间倒序返回最多两条，并持久化证据包。缺少精确时间显式提示，少于两条返回不足。
- 当前仅返回结果，不执行差值或诊断推断；手动导入没有同步水位，coverage明确标为unknown。
- 通过服务端配置的token绑定机构、操作者、患者和权限；证据原文回查再次检查权限。尚未对接医院身份系统、数据库RLS或用途审批。

## PostgreSQL 验证路径（本次未实机执行）

从项目根目录启动：

```bash
export POSTGRES_PASSWORD='replace-with-local-password'
docker compose -f deploy/compose.yaml up -d
cd back
export DATABASE_URL='postgresql+psycopg://evidence:replace-with-local-password@127.0.0.1:5432/medical_evidence'
python3 -m alembic upgrade head
python3 -m app.demo
```

然后按上面的方式启动API并执行三条curl，检查持久化记录及引用。当前pytest仍使用SQLite内存库，不能把其结果当作PostgreSQL测试结果。Docker镜像版本为开发配置，部署前需固定已审核的补丁版本/摘要。

## 测试与剩余限制

本次12项测试通过；覆盖写入、版本、外键、错误来源、重复导入、单次结果、撤销报告和未授权调用。环境有一条第三方测试客户端弃用警告，不影响本次测试结果。

仍需：完整临床字段映射、执行产物哈希强制检查、查询发布审批服务、跨系统重复事件识别、并发一致性快照、源同步水位、批量导入限额、数据库访问角色/RLS、访问审计、生产异常处理与PostgreSQL集成测试。当前一次查询可能执行多次读取，生产快照一致性尚未保证；snapshot_id是结果包标识，不应理解成已实现数据库时间旅行。

demo初始化将查询标为演示发布，审核字段明确为demo，不代表临床验证或真人审批。不可用于自动生成真实审批记录。
