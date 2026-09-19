from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from procureflow.api.deps import get_db
from procureflow.models.audit import AuditLog

router = APIRouter(prefix="/audit", tags=["Audit"])


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    rfq_id: str
    event_type: str
    actor_type: str
    timestamp: datetime


class AuditPage(BaseModel):
    items: list[AuditEventRead]
    total: int
    page: int
    page_size: int


@router.get("", response_model=AuditPage)
async def list_audit_events(
    rfq_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> AuditPage:
    query = select(AuditLog)
    count = select(func.count()).select_from(AuditLog)
    if rfq_id:
        query = query.where(AuditLog.rfq_id == rfq_id)
        count = count.where(AuditLog.rfq_id == rfq_id)
    total = (await db.execute(count)).scalar_one()
    events = (
        (
            await db.execute(
                query.order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return AuditPage(
        items=[AuditEventRead.model_validate(event) for event in events],
        total=total,
        page=page,
        page_size=page_size,
    )
