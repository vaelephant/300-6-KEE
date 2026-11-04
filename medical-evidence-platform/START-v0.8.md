# V0.8 前端工作台拆分

本版重点为前端功能组织：资产库、质量审核、证据查询三条独立路由，共用当前会话的凭证、患者与就诊选择。不新增模拟成功结果。

## 页面

| 路径 | 功能 |
|---|---|
| /assets | PDF上传、文档列表、解析状态、OCR、原页浏览；合成检验JSON导入 |
| /quality | OCR区域审核队列、状态筛选、逐条原页核对、确认/纠正/驳回、审核历史 |
| /evidence | 最近两次肌酐、来源核对、文档关键词检索和原页定位 |

根路径自动跳到/assets。刷新浏览器需重新连接，凭证不写入localStorage或磁盘。页面间正常导航保留连接与患者选择；当前页结果在离开后重新加载。

## 启动升级

终端一：沿用原DATABASE_URL与数据库文件，不要覆盖旧数据。

```bash
cd medical-evidence-platform/back
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m alembic upgrade head
python3 -m app.demo
export EVIDENCE_PRINCIPALS_JSON='{"local-demo-token":{"tenant_id":"hospital_demo","actor_id":"developer","patients":["patient_demo"],"permissions":["read","ingest","review"]}}'
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

首次安装先python3 -m venv .venv。终端二：

```bash
cd medical-evidence-platform/front
npm ci
npm run dev
```

访问http://127.0.0.1:3000。OCR系统依赖及语言包沿用START-v0.6.md。本轮没有新数据库迁移，upgrade用于确保已有表升级到0006。

## 建议验收流程

1. 在资产库连接local-demo-token并选择patient_demo。
2. 上传06-scanned-report.pdf，英文OCR完成后切换审核页，患者与连接状态应保留。
3. 待审核队列无需关键词，选择区域查看原页。
4. 填写说明并确认或纠正，保存后该项从待审队列消失；切换“已确认/已纠正”可回看。
5. 点击下一条待核对区域，或从左侧列表选择其他区域继续。
6. 输入未保存内容后切换左侧导航、患者、就诊或关闭页面，应出现确认提醒。
7. 切换证据查询页，检索有效文字并核对来源；检验查询继续使用既有JSON示例。

## 实现位置

- front/app/Session.js：跨路由会话上下文。
- front/app/Workspace.js：公共导航、连接、患者范围及检验查询。
- front/app/assets、quality、evidence：三个路由入口。
- front/app/Documents.js：按工作区显示资产管理、审核或文档查询。
- back/app/reviews.py：新增POST /v1/documents/review-queue，支持患者、状态、offset、limit。

队列仅含OCR区域，普通PDF文字没有混入待审任务。列队查询需要read权限，提交仍需要review权限。采用offset分页，审核后重新刷新第一页；不宣称并发编辑下的稳定快照分页。

## 验证与未覆盖部分

22项后端测试通过，新增待审队列、审核后状态迁移和患者权限测试。三页面Next生产构建通过。浏览器可执行文件不可用，未完成浏览器交互自动化与视觉截图验收；PostgreSQL仍待实机验证。

这是前端工作区首版：尚无总览仪表盘、完整多模态类型筛选、源系统管理、血缘页面、患者时间轴、SSO和问答页。当前资产库仅PDF，检验数据入口仍为合成JSON；没有伪装成已实现的影像或音视频管理。

审核区采用列表与原页面板，审核表单在原页上方；不是三栏固定高度专业阅片器。导航和范围切换有未保存提醒，浏览器后退等特殊导航尚未完整覆盖。文档检索和审核队列按患者范围，上方就诊选择用于导入归属与检验查询，暂不作为文档筛选。OCR、审核与权限的生产限制继承前版说明。
