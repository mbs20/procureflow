from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ServiceStatus(BaseModel):
    status: str = Field(..., example="healthy")
    latency_ms: float | None = Field(None, example=2.5)
    details: str | None = None


class HealthResponse(BaseModel):
    status: str = Field(..., example="ok")
    version: str = Field(..., example="0.1.0")
    environment: str = Field(..., example="development")
    database: ServiceStatus
    redis: ServiceStatus
    celery: ServiceStatus


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int
