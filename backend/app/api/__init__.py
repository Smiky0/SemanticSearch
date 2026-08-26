from fastapi import APIRouter

from app.api.explain_api import router as explain_router
from app.api.graph_api import router as graph_router
from app.api.repository_api import router as repository_router
from app.api.search_api import router as search_router
from app.api.symbol_api import router as symbol_router
from app.api.trace_api import router as trace_router

router = APIRouter()

router.include_router(repository_router)
router.include_router(search_router)
router.include_router(explain_router)
router.include_router(trace_router)
router.include_router(graph_router)
router.include_router(symbol_router)
