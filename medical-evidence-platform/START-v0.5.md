# V0.5 文档资产管理

本轮新增患者文档列表、分页浏览、解析状态及同范围PDF幂等导入。未实现OCR、PDF临床事实抽取或大模型问答。

## 升级

保留旧数据库，使用新包代码，在原数据库连接配置下执行：

```bash
cd medical-evidence-platform/back
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m alembic upgrade head
python3 -m app.demo
export EVIDENCE_PRINCIPALS_JSON='{"local-demo-token":{"tenant_id":"hospital_demo","actor_id":"developer","patients":["patient_demo"],"permissions":["read","ingest"]}}'
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

首次安装先运行 python3 -m venv .venv。新解压目录不会自动带入旧SQLite文件，需保持原DATABASE_URL指向已有文件；不要删除旧数据。

另一个终端：

```bash
cd medical-evidence-platform/front
npm ci
npm run dev
```

访问 http://127.0.0.1:3000，连接并选择患者，在PDF面板查看文档列表。上传后自动刷新；点击“浏览原页”可以上一页/下一页。待OCR文档也可以直接打开原页。

## 数据与接口

新增 POST /v1/documents/list，参数 patient_id、offset（默认0）、limit（默认20，上限100）。返回文档名、页数、状态、版本ID、入库时间、就诊ID以及next_offset。列表和原页均按当前凭证鉴权。

新增0004迁移及document_import_keys表。幂等键由患者ID、就诊ID和原始文件SHA-256生成，外加租户复合主键。文件名不是去重依据；同范围同字节文件返回unchanged并保留首次名称。不同患者、不同就诊或不同字节不会合并。新内容当前创建新资产，不自动推断临床修订关系。

数据库唯一约束处理竞争，事务失败时回滚新建资产，再尝试读取已存在映射。幂等命中不重复解析。旧文件迁移时建立映射，历史重复资产保留；同组按资产版本ID顺序选择一个复用对象。迁移在线读取历史PDF内容计算哈希，大量数据时应在维护窗口或分批改造后执行；本版不支持该迁移的离线SQL生成。

## 验收步骤

1. 导入05-synthetic-report.pdf，文档列表应出现一条记录。
2. 再次导入同文件，提示文件已存在，资产ID相同，列表数量不增加。
3. 浏览原页，再以Creatinine搜索并打开命中区域。
4. 导入无文字PDF，列表显示待OCR，仍能浏览页面；未启动OCR服务。
5. 使用无该患者权限的凭证访问列表或原页，应拒绝。

## 已验证与限制

18项后端测试通过；SQLite从V0.4升级到0004通过。前端生产构建通过。新增测试覆盖重复上传、列表权限、分页和无文字文档回看。并发竞争逻辑有数据库约束，但本轮未做并发压力测试。未进行PostgreSQL实机验证和浏览器完整视觉回归。

列表为offset分页，并发新增时可能发生跨页变化；刷新回第一页重新获取。搜索仍以患者为范围，不按就诊筛选。解析仍同步执行，原有大小/页数/版面限制继续有效。部署安全及源身份核验等限制见START-v0.4.md。
