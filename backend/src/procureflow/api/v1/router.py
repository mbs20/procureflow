from fastapi import APIRouter

from procureflow.api.v1.health import router as health_router
from procureflow.api.v1.matrix import router as matrix_router
from procureflow.api.v1.quotations import router as quotations_router
from procureflow.api.v1.rfqs import router as rfqs_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(rfqs_router)
api_v1_router.include_router(quotations_router)
api_v1_router.include_router(matrix_router)
