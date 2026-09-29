from fastapi import APIRouter
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.system import router as system_router
from app.api.v1.documents import router as documents_router
from app.api.v1.graph import router as graph_router
from app.api.v1.trust import router as trust_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.models import router as models_router
router=APIRouter(); router.include_router(knowledge_router); router.include_router(documents_router); router.include_router(jobs_router); router.include_router(models_router); router.include_router(system_router); router.include_router(graph_router); router.include_router(trust_router)

from app.api.v1.operations import router as operations_router
router.include_router(operations_router)

from app.api.v1.runtime import router as runtime_router
router.include_router(runtime_router)
