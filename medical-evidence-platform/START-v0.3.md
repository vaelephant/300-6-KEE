# V0.3 证据查询工作台

前端 Next.js，后端 FastAPI，保留 front/back 分离。后端沿用V0.2，新增授权患者与就诊列表。前端通过同源服务端代理访问固定白名单API，浏览器不直接连接数据库。

## 1. 启动后端（终端一）

```bash
cd medical-evidence-platform/back
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m alembic upgrade head
python3 -m app.demo
export EVIDENCE_PRINCIPALS_JSON='{"local-demo-token":{"tenant_id":"hospital_demo","actor_id":"developer","patients":["patient_demo"],"permissions":["read","ingest"]}}'
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

已有V0.2环境可复用虚拟环境与数据库；请用本包后端代码以获得 /v1/patients 接口。不要把旧development.db覆盖到新数据上；保持原DATABASE_URL。初始化只补充示例患者和查询，不清空已有数据。

## 2. 启动前端（终端二）

```bash
cd medical-evidence-platform/front
npm ci
npm run dev
```

打开 http://127.0.0.1:3000，输入 local-demo-token，点击“连接平台”。生产构建可运行 npm run build 后 npm start。Node建议使用支持本项目Next版本的LTS运行时，已在Node24测试构建。

后端地址默认 http://127.0.0.1:8000；如需修改，在front/.env.local配置 BACKEND_URL=http://实际后端地址:端口。不要将后端Token写入NEXT_PUBLIC变量。示例Token仅限本地合成数据演示。

## 3. 页面操作

1. 连接后选择 patient_demo，默认查询全部授权就诊。
2. 导入 demo-data/01-one-result.json，查询可见一次结果及不足提示。
3. 导入 02-two-results.json；已存在的相同版本不重复写入，查询可见92、86。
4. 导入 03-corrected.json，查询变为90、86，来源版本为V2。
5. 导入 04-cancelled.json，查询仅剩86，不会回退显示被撤销的92或90。
6. 点击“查看来源”，右侧高亮result_value，并显示原记录、资产版本及完整元数据。

上述预期假定数据库没有其他更新日期的记录；如之前导入旧版demo-ingest.json，2026-10-01记录会进入最近两次列表。若需独立演示，请设置新DATABASE_URL=sqlite:///workbench-demo.db，再迁移初始化，不要删除原数据库。四个文件应按顺序导入，修订文件依赖前序版本。

批量导入最多20条、文件限2MB，逐条提交；失败前的成功记录保留，并在页面说明已处理数量。Token仅保存在页面内存，刷新/退出需重新输入。资产和血缘导航当前仅为布局占位，非已实现页面。

## 4. 验证及边界

已通过Next生产构建与14项后端测试，涵盖患者授权列表及两次结果、更正、撤销。数据库测试仍为SQLite，PostgreSQL尚未实机验证。沿用V0.2的数据权限和源字段映射限制，本次未加入医院SSO、PDF解析、大模型问答或完整血缘管理页面。

正式部署须使用HTTPS、医院身份认证与受控网络，并完成前述生产约束。本版为本地开发演示。

附加验证：已通过真实HTTP的前端代理→后端→导入/查询/来源回查联调，更正前结果92、86，更正后90、86，撤销后86。浏览器安装下载失败，未完成真实浏览器视觉检查。
