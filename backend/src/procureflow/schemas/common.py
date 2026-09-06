from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ServiceStatus(BaseModel):
    status: str = Field(..., examples=["healthy"])
    latency_ms: float | None = Field(None, examples=[2.5])
    details: str | None = None


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])
    version: str = Field(..., examples=["0.1.0"])
    environment: str = Field(..., examples=["development"])
    database: ServiceStatus
    redis: ServiceStatus
    celery: ServiceStatus


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int
