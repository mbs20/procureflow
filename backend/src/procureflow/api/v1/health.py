import time

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from procureflow.config import get_settings
from procureflow.database import get_db
from procureflow.schemas.common import HealthResponse, ServiceStatus

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """Comprehensive health check endpoint checking DB, Redis, and Celery."""
    # 1. Check Database
    db_status = ServiceStatus(status="unknown")
    try:
        t0 = time.perf_counter()
        await db.execute(text("SELECT 1"))
        latency = (time.perf_counter() - t0) * 1000
        db_status = ServiceStatus(status="healthy", latency_ms=round(latency, 2))
    except Exception as exc:
        db_status = ServiceStatus(status="unhealthy", details=str(exc))

    # 2. Check Redis
    redis_status = ServiceStatus(status="unknown")
    try:
        t0 = time.perf_counter()
        r = aioredis.from_url(settings.redis_url, socket_timeout=2.0)
        await r.ping()
        await r.close()
        latency = (time.perf_counter() - t0) * 1000
        redis_status = ServiceStatus(status="healthy", latency_ms=round(latency, 2))
    except Exception as exc:
        # If in development with eager tasks, note that Redis is optional
        if settings.celery_always_eager:
            redis_status = ServiceStatus(status="skipped_in_eager_mode", details=str(exc))
        else:
            redis_status = ServiceStatus(status="unhealthy", details=str(exc))

    # 3. Check Celery Configuration
    celery_status = ServiceStatus(
        status="configured_eager" if settings.celery_always_eager else "configured_distributed",
        details=f"Broker: {settings.celery_broker_url}",
    )

    overall_status = "healthy" if db_status.status == "healthy" else "degraded"

    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        environment=settings.environment,
        database=db_status,
        redis=redis_status,
        celery=celery_status,
    )
