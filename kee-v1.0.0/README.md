# Knowledge Evolution Engine (KEE) v1.0.0

A runnable full-stack knowledge runtime for AI Agents: ingestion → understanding → knowledge objects → evidence/provenance → evolution/review → trust → hybrid retrieval → grounded context packs.

## What is included

- `front/` Next.js console with Dashboard, Knowledge Graph, Trust Intelligence, ingestion, evolution and Agent Runtime Context Builder.
- `back/` FastAPI API with SQLite default persistence and optional PostgreSQL/pgvector, Neo4j sync and BGE-M3 / OpenAI-compatible embedding hooks.
- **Redis + arq** job queue for document ingest (upload returns `job_id` immediately).
- **System → Models** UI/API for LLM & Embedding configuration (persisted to `data/model_settings.json`).
- Grounded Agent API: `POST /api/v1/runtime/context` and `POST /api/v1/runtime/agent`.

## Run locally (3 processes)

Default ports: **backend `8306`**, **frontend `3030`**, Redis via compose on **`16379`**.

The browser talks to **same-origin** `/api/v1`; Next rewrites to the backend (`KEE_BACKEND_URL`).

### 1. Infra (Postgres + Redis + Neo4j)

```bash
cd back
docker compose up -d
cp .env.example .env   # points at remapped ports
```

| Service  | Host port |
|----------|-----------|
| Postgres | `15432`   |
| Redis    | `16379`   |
| Neo4j    | `17687` (Bolt), `17474` (HTTP) |

SQLite-only demo: set `DATABASE_URL=sqlite+pysqlite:///./data/kee.db` and still run Redis (required for uploads).

### 2. API

```bash
cd back
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8306
```

### 3. Queue worker (required for document upload)

```bash
cd back
source .venv/bin/activate
arq app.workers.tasks.WorkerSettings
```

Without the worker, uploads enqueue but stay `queued`.

### 4. Frontend

```bash
cd front
cp .env.example .env.local
pnpm install
pnpm run dev --port 3030
```

- Console: http://localhost:3030  
- System Links + Models: http://localhost:3030/system  
- Agent Runtime: http://localhost:3030/runtime  
- API docs: http://127.0.0.1:8306/docs  

### 快捷重启

```bash
# API
cd back
lsof -t -i:8306 | xargs kill -9 2>/dev/null; clear
source .venv/bin/activate
uvicorn app.main:app --reload --port 8306

# Worker (separate terminal)
cd back && source .venv/bin/activate
python -m arq app.workers.tasks.WorkerSettings

# Front
cd front
lsof -t -i:3030 | xargs kill -9 2>/dev/null; clear
pnpm run dev --port 3030
```

## Models

Configure via **System Links** page or:

- `GET/PUT /api/v1/system/models`
- `POST /api/v1/system/models/list` — `{ "target":"llm", "base_url":"...", "api_key":"..." }` → remote model ids
- `POST /api/v1/system/models/test` with `{"target":"llm"|"embedding"}`

Flow: enter Base URL + Key → **List models** → pick from dropdown → **Save**.

## Jobs

- Upload: `POST /api/v1/documents/upload` → `{ job_id, document_id, status: "queued" }`
- Poll: `GET /api/v1/jobs/{job_id}`
- List: `GET /api/v1/jobs?document_id=`

Redis down → upload returns **503** (no silent sync fallback).

## Notes

- **Postgres** is the live store when configured (SQLite data is not auto-migrated).
- **Neo4j** syncs on save when `ENABLE_NEO4J_SYNC=true`.
- **Redis** is the **arq** queue for ingest.
- **pgvector** image is used; default embedding remains local hash until you switch provider in Models.

## Production notes

Auth/SSO, tenant isolation, formal migrations, backups and observability should still be hardened for the target environment.
