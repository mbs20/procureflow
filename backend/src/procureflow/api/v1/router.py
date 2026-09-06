from fastapi import APIRouter

from procureflow.api.v1.health import router as health_router
from procureflow.api.v1.rfqs import router as rfqs_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(rfqs_router)
