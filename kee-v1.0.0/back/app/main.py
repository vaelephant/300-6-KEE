from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import router
from app.core.config import settings
from app.db.session import init_db
@asynccontextmanager
async def lifespan(app):
 init_db(); yield
init_db()
app=FastAPI(title=settings.app_name,version="1.0.0",description="Knowledge Evolution Engine backend",lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in settings.cors_origins.split(",")],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(router,prefix="/api/v1")
@app.get("/health")
async def health(): return {"status":"ok","service":"kee-back","version":"1.0.0","persistence":"database","runtime":"agent-knowledge-runtime"}
