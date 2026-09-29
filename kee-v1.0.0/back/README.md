# KEE Backend

FastAPI backend for Knowledge Evolution Engine: ingest queue (Redis/arq), evolution pipeline, models overlay, agent runtime APIs.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# optional: docker compose up -d
uvicorn app.main:app --reload --port 8306
```

Queue worker (required for document upload):

```bash
source .venv/bin/activate
python -m arq app.workers.tasks.WorkerSettings
# or: .venv/bin/arq app.workers.tasks.WorkerSettings
```

Open http://127.0.0.1:8306/docs

## Core APIs

- `POST /api/v1/documents/upload` → queued job
- `GET /api/v1/jobs/{id}`
- `GET|PUT /api/v1/system/models` · `POST /api/v1/system/models/test`
- `POST /api/v1/knowledge/evolve` · `query` · `feedback` · review
- `POST /api/v1/documents/upload` → Redis job; poll `GET /api/v1/jobs/{id}`（含 `logs` / `phase` / `progress`）
- Worker 控制台日志 logger=`kee.ingest`（重启 arq 后生效）
- `GET /api/v1/runtime/readiness`
- `POST /api/v1/runtime/context` — context pack for console / callers
- `POST /api/v1/runtime/agent` — same pack + `kee-agent-context/1.0` protocol wrapper

## Agent 插件（MCP）

代码在 `app/mcp/`：`mcp_server.py`（stdio + 工具）、`mcp_context.py`（取 pack）。

KEE 作为 Agent 出口插件：工具 `kee_get_context` 返回带信任过滤与引用的 context pack（不代答）。默认 **进程内** 调 `RuntimeService`（与 backend 共用 `DATABASE_URL`）。

```bash
cd kee-v1.0.0/back
source .venv/bin/activate
python -m app.mcp
```

Cursor / Claude Desktop `mcp.json` 示例（路径按本机修改）：

```json
{
  "mcpServers": {
    "kee": {
      "command": "/ABS/PATH/kee-v1.0.0/back/.venv/bin/python",
      "args": ["-m", "app.mcp"],
      "cwd": "/ABS/PATH/kee-v1.0.0/back",
      "env": {
        "DATABASE_URL": "sqlite+pysqlite:///./data/kee.db"
      }
    }
  }
}
```

远程模式（MCP 独立进程打 HTTP）：设 `KEE_API_BASE=http://127.0.0.1:8306`，可选 `KEE_API_KEY`（`Authorization: Bearer …`）。

工具参数：`question`（必填）、`top_k`、`min_trust`、`domain`、`include_guarded`。  
返回：`{ protocol, instructions, context_pack }`；`context_pack.grounded=false` 时宿主应声明证据不足。
