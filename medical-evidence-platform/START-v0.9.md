# V0.9 可信查询工具与问答闭环

新增 /assistant。支持规则演示、服务端模型工具调用、带引用回答、原始记录/PDF定位与回答快照。沿用现有前端风格，尚未实现概念图中的总览仪表盘。

## 升级

保留原数据库，在 back 目录、原虚拟环境执行：

```bash
python3 -m pip install -r requirements.txt
python3 -m alembic upgrade head
```

本次新增迁移 0007：answer_snapshots。沿用 START-v0.8.md 的凭证配置与启动方式。重启后端和前端，进入 /assistant。若没有示例数据，先运行 `python3 -m app.demo` 并在资产库导入 demo-data 中的检验 JSON 或 PDF。

## 接入模型

默认演示模式不使用模型、不需要模型密钥。肌酐问题调用固定查询；其他输入原样作为文档关键词。

真实模式使用兼容 Chat Completions 的服务端接口，须支持 function tools、tool_choice=required 以及 JSON 文本回答。启动后端前配置：

```bash
export MODEL_BASE_URL='http://127.0.0.1:8080/v1'
export MODEL_NAME='your-tool-capable-model'
read -s MODEL_API_KEY
export MODEL_API_KEY
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

地址是示例，请改为你自己的模型服务。MODEL_BASE_URL 后自动追加 /chat/completions。密钥仅在后端读取；选择真实模式会将问题与检索出的证据片段发往配置的模型服务。医疗数据应使用医院批准的部署。当前没有指定供应商 SDK，也未完成真实模型联调。

## API

全部使用原有 Bearer 凭证。

- GET /v1/assistant/tools：工具定义和模型配置状态。
- POST /v1/assistant/ask：`{"patient_id":"patient_demo","question":"最近两次肌酐是多少？","mode":"demo"}`。mode=model 开启真实模型。
- GET /v1/assistant/answers/{answer_id}：按租户及患者权限读取已保存回答快照。

工具 query_lab_results 当前仅支持最近两次有效血清肌酐，不是任意检验工具。search_clinical_evidence 为文档原文关键词匹配，不是语义检索。两个工具共用现有查询实现；租户/患者/操作者由服务端绑定，工具参数不允许覆盖患者。

一轮最多三次工具调用，两次模型请求；每次模型请求超时40秒。不支持连续自主循环或任意 SQL。文档最多返回12段，未经确认或纠正的OCR排除，PDF原生文字仍可能未经人工核对；当前存在先检索100条再筛OCR的召回限制。查询限定当前患者全部就诊。

每条模型陈述必须引用本次工具返回的证据ID；ID无效或格式错误时整体回退证据摘录。此校验不是事实蕴含验证，不保证模型没有曲解证据。没有证据时展示不足说明，不将“没有查到”转换成“患者没有”。来源文字按不可信数据处理，但尚未做完整的提示注入红队评测。

回答快照存储问题、证据、工具结果、模型输出和限制。它是应用结果存档，不代表多次工具查询处于同一个数据库事务快照。模型服务失败不伪装成规则模式成功；已完成的底层检验查询记录可能保留。文档审核可能在查询后变化，回答快照保留当时的审核版本与文本。

## 手工验收

1. 连接 local-demo-token，选择 patient_demo，导入两次肌酐示例。
2. /assistant 规则演示查询最近两次肌酐，点击引用查看原始字段。
3. 导入 PDF，以实际英文关键词 Creatinine 检索，点击引用查看页码与区域。
4. 无命中时确认显示证据不足；不能返回否定诊断。
5. 配置支持工具调用的模型并重启后端，重新进入页面，切换真实模型，观察工具记录与回答引用。
6. 保存 answer_id，使用快照接口重新读取；更换无患者权限凭证应拒绝。

本轮自动测试结果见交付说明。浏览器交互与视觉验收、真实模型服务及 PostgreSQL 实机测试仍需执行。当前是可运行开发版，尚无MCP适配、通用指标目录、SSO或全模态问答。

## 本轮验证结果

26项后端测试通过；Next.js生产构建通过；SQLite空库迁移至0007通过。真实模型调用使用模拟响应验证工具协议及引用分支，未使用真实模型服务。
