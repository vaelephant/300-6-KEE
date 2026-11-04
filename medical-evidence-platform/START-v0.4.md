# V0.4 PDF文档证据

在V0.3工作台底部新增PDF导入、关键词检索、原页查看和区域高亮。保留检验查询功能。文档片段是原始证据，不是自动确诊事实；未接大模型。

## 升级启动

终端一：

```bash
cd medical-evidence-platform/back
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m alembic upgrade head
python3 -m app.demo
export EVIDENCE_PRINCIPALS_JSON='{"local-demo-token":{"tenant_id":"hospital_demo","actor_id":"developer","patients":["patient_demo"],"permissions":["read","ingest"]}}'
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

如果新解压目录没有虚拟环境，先执行 python3 -m venv .venv。旧数据库请通过原DATABASE_URL继续使用，并运行迁移；不要覆盖或删除旧数据库文件。

终端二：

```bash
cd medical-evidence-platform/front
npm ci
npm run dev
```

打开 http://127.0.0.1:3000，连接后选择患者。在PDF文档证据面板上传 demo-data/05-synthetic-report.pdf，输入 Creatinine 检索，点击“打开原页并定位”。右侧应显示原页，并在相应文本行上高亮。

## 本轮新增

- 0003迁移：document_files存原始PDF字节，document_blocks存文字区域及锚点关联。
- POST /v1/documents/import：在已授权患者下导入PDF，返回页数、区域数、解析状态和无文本页号。
- POST /v1/documents/search：患者范围内的字面关键词匹配，最多100条并返回截断标志。
- GET /v1/documents/{asset_version_id}/pages/{page}：每次重新鉴权，渲染PNG，不暴露持久公开链接。
- 来源页号从1开始，归一化左上角坐标，解析器版本绑定到来源锚点。

## 支持边界

支持有文字层、未旋转且无裁切偏移的PDF。单文件5MB/50页。扫描件无文字时保留原文件并标 needs_ocr；混合文件标 partial_text，检索提示覆盖不完整。尚无OCR实现，不应将无命中解释为没有临床记录。图形无文本页面也可能需要人工判断，不一定都是扫描件。

当前按文字行创建证据，未处理跨行医学实体与复杂表格语义；中文检索请使用原文中的短关键词。显示的高亮为命中整行区域。每次导入创建新资产，不自动去重或与旧文档建立修订关系。

页面搜索以患者为范围，不限制上方就诊选择；上传时使用当前就诊关联。UI已明确患者范围。所属患者由操作人员选择，系统目前不会从PDF正文验证身份，应使用合成数据。

解析和页面渲染同步执行，虽然有文件/页数限制，仍未实现隔离进程、恶意文件扫描和硬超时；代理15秒超时不意味着后台事务自动取消。超时后勿盲目重复导入。正式上线前需异步任务和幂等导入设计。

pdfplumber/PDFium负责解析和渲染，未引入PyMuPDF到项目依赖。依赖许可与医院部署要求需按实际版本审核。存储暂用数据库二进制列，后续可迁移到受控对象存储。

PostgreSQL仍待实机验证，继承V0.3生产限制。

本轮验证：16项后端测试通过，Next生产构建通过，SQLite迁移升级通过，示例PDF渲染并人工检查。未进行浏览器端完整交互和高亮截图验证；未进行PostgreSQL实机验证。
