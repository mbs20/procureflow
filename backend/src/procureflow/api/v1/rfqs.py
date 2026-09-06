import math

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from procureflow.api.deps import get_db, verify_api_key
from procureflow.models.rfq import RFQStatus
from procureflow.schemas.common import PaginatedResponse
from procureflow.schemas.rfq import (
    CriterionCreate,
    RFQCreate,
    RFQRead,
    RFQUpdate,
)
from procureflow.services.rfq_service import (
    archive_rfq,
    clone_rfq,
    create_rfq,
    get_rfq_or_404,
    list_rfqs,
    unarchive_rfq,
    update_criteria,
    update_rfq,
)

router = APIRouter(prefix="/rfqs", tags=["RFQs"])


@router.post(
    "",
    response_model=RFQRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new RFQ",
)
async def create_rfq_endpoint(
    rfq_in: RFQCreate,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> RFQRead:
    """Create a new RFQ with its required line items and weighted evaluation criteria."""
    rfq = await create_rfq(db=db, rfq_in=rfq_in, actor_id=api_key)
    return RFQRead.model_validate(rfq)


@router.get(
    "",
    response_model=PaginatedResponse[RFQRead],
    summary="List all RFQs",
)
async def list_rfqs_endpoint(
    include_archived: bool = Query(
        False, description="Whether to include soft-deleted/archived RFQs"
    ),
    status_filter: RFQStatus | None = Query(
        None, alias="status", description="Filter by RFQ status"
    ),
    category: str | None = Query(None, description="Search by category"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[RFQRead]:
    """List and search RFQs with pagination, status filters, and soft-delete exclusions."""
    skip = (page - 1) * page_size
    items, total = await list_rfqs(
        db=db,
        include_archived=include_archived,
        status_filter=status_filter,
        category=category,
        skip=skip,
        limit=page_size,
    )
    pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedResponse(
        items=[RFQRead.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{rfq_id}",
    response_model=RFQRead,
    summary="Get RFQ by ID",
)
async def get_rfq_endpoint(
    rfq_id: str,
    db: AsyncSession = Depends(get_db),
) -> RFQRead:
    """Get complete details of a specific RFQ including all line items and criteria."""
    rfq = await get_rfq_or_404(db=db, rfq_id=rfq_id)
    return RFQRead.model_validate(rfq)


@router.patch(
    "/{rfq_id}",
    response_model=RFQRead,
    summary="Update RFQ metadata",
)
async def update_rfq_endpoint(
    rfq_id: str,
    update_data: RFQUpdate,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> RFQRead:
    """Update title, description, category, currency, or status of an RFQ."""
    rfq = await update_rfq(db=db, rfq_id=rfq_id, update_data=update_data, actor_id=api_key)
    return RFQRead.model_validate(rfq)


@router.post(
    "/{rfq_id}/archive",
    response_model=RFQRead,
    summary="Archive RFQ (soft delete)",
)
async def archive_rfq_endpoint(
    rfq_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> RFQRead:
    """Soft-delete an RFQ. Preserves historical quotations, extractions, and decisions in the audit log."""
    rfq = await archive_rfq(db=db, rfq_id=rfq_id, actor_id=api_key)
    return RFQRead.model_validate(rfq)


@router.post(
    "/{rfq_id}/unarchive",
    response_model=RFQRead,
    summary="Restore archived RFQ",
)
async def unarchive_rfq_endpoint(
    rfq_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> RFQRead:
    """Restore an archived RFQ back to active status."""
    rfq = await unarchive_rfq(db=db, rfq_id=rfq_id, actor_id=api_key)
    return RFQRead.model_validate(rfq)


@router.post(
    "/{rfq_id}/clone",
    response_model=RFQRead,
    status_code=status.HTTP_201_CREATED,
    summary="Clone RFQ template",
)
async def clone_rfq_endpoint(
    rfq_id: str,
    new_title: str | None = Query(None, description="Title for cloned RFQ"),
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> RFQRead:
    """Clone an existing RFQ structure, line items, and criteria to a new draft RFQ."""
    cloned = await clone_rfq(db=db, rfq_id=rfq_id, new_title=new_title, actor_id=api_key)
    return RFQRead.model_validate(cloned)


@router.put(
    "/{rfq_id}/criteria",
    response_model=RFQRead,
    summary="Update evaluation criteria",
)
async def update_criteria_endpoint(
    rfq_id: str,
    criteria_in: list[CriterionCreate],
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key),
) -> RFQRead:
    """Replace all evaluation criteria. Enforces that weights sum to exactly 1.00 (100%)."""
    rfq = await update_criteria(db=db, rfq_id=rfq_id, criteria_in=criteria_in, actor_id=api_key)
    return RFQRead.model_validate(rfq)
