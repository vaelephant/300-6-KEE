# V0.6 扫描件OCR

新增文档OCR按钮及OCR运行记录。OCR只针对完全没有已提取文字的页面，识别结果作为来源区域与文本索引保存，不转换为诊断或检验事实，原始PDF字节及其哈希不变。

## 系统依赖

本地需安装Tesseract。macOS可运行：

```bash
brew install tesseract
brew install tesseract-lang
tesseract --list-langs
```

Ubuntu可由管理员安装 tesseract-ocr、tesseract-ocr-eng、tesseract-ocr-chi-sim。选择中文+英文前，检查语言列表中同时存在chi_sim与eng。缺少语言包时接口明确报错，不会静默用英文替代。

## 升级

沿用原DATABASE_URL并保留旧数据：

```bash
cd medical-evidence-platform/back
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m alembic upgrade head
python3 -m app.demo
export EVIDENCE_PRINCIPALS_JSON='{"local-demo-token":{"tenant_id":"hospital_demo","actor_id":"developer","patients":["patient_demo"],"permissions":["read","ingest"]}}'
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

首次安装先建虚拟环境。另一个终端运行front中的npm ci、npm run dev，打开http://127.0.0.1:3000。

## 演示验收

1. 上传demo-data/06-scanned-report.pdf，列表应标记待OCR。
2. 选择英文eng，点击该文档的“执行OCR”。
3. 等待状态更新为OCR完成·未审核。
4. 检索Creatinine，结果应带“OCR识别·未审核”标识。
5. 打开命中原页，人工核对86、单位与原文。
6. 所有页面都有文字后，重复请求返回unchanged，不重复写入。

新增POST /v1/documents/ocr，参数asset_version_id、language。要求患者范围内的ingest权限。0005迁移增加document_ocr_runs：保存输入资产版本、引擎版本、语言、运行时间、页面、区域文字及识别分值。分值只作引擎诊断，不能当作临床真实性概率。

## 执行限制

本版为同步演示，每个文档最多处理3个无文字页，每页Tesseract子进程超时40秒；总预算检查发生在页间，渲染本身未隔离硬超时。前端代理等待150秒。进程内锁防止同一服务进程同时运行多项OCR；暂不支持多worker或多副本并发OCR，生产前需分布式任务队列、幂等任务与隔离进程。

如果页面已有少量文字但图片区域仍有文字，本版会跳过整页，无法保证完整识别。只支持印刷体演示，不承诺手写、多栏或复杂表格准确度。采用PSM6，没有版面分类。OCR结果未审核，不应直接用于临床结论。

失败事务回滚，不保留完成记录；失败审计/任务重试队列尚未实现。成功但无文字的页面可再试，新的运行记录保留。已有文字不自动覆盖，尚无重识别/纠错与版本替代界面。document_files.status是可变处理状态，原始资产版本不被修改。

当前环境仅有英文语言包：英文图片PDF识别、检索和定位关联实测通过；中文仅实现语言选择和缺失检查，尚未中文数据实测。19项后端测试、Next生产构建和SQLite迁移通过。未完成PostgreSQL实机验证或浏览器端完整视觉回归。保留前几版生产权限和身份核验限制。
