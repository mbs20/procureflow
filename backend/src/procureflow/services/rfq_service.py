from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from procureflow.models.rfq import (
    RFQ,
    EvaluationCriterion,
    RFQLineItem,
    RFQStatus,
)
from procureflow.schemas.rfq import (
    CriterionCreate,
    RFQCreate,
    RFQUpdate,
)
from procureflow.services.audit_service import record_audit_event


def validate_criteria_weights(criteria: list[CriterionCreate]) -> None:
    """Validate that criterion weights sum to 1.00 ± 0.001."""
    if not criteria:
        return
    total_weight = sum(Decimal(str(c.weight)) for c in criteria)
    if abs(total_weight - Decimal("1.0")) > Decimal("0.001"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Evaluation criteria weights must sum to 1.00 (current total: {total_weight})",
        )


async def create_rfq(
    db: AsyncSession,
    rfq_in: RFQCreate,
    actor_id: str = "system",
) -> RFQ:
    """Create a new RFQ with its line items, criteria, and audit trail entry."""
    validate_criteria_weights(rfq_in.criteria)

    rfq = RFQ(
        title=rfq_in.title,
        description=rfq_in.description,
        category=rfq_in.category,
        status=RFQStatus.DRAFT,
        reference_currency=rfq_in.reference_currency.upper(),
        created_by=actor_id,
        is_archived=False,
    )
    db.add(rfq)
    await db.flush()

    # Add line items with sequenced positions
    for idx, item in enumerate(rfq_in.line_items, start=1):
        line_item = RFQLineItem(
            rfq_id=rfq.id,
            position=item.position or idx,
            description=item.description,
            quantity=item.quantity,
            unit=item.unit,
        )
        db.add(line_item)

    # Add criteria
    for crit in rfq_in.criteria:
        criterion = EvaluationCriterion(
            rfq_id=rfq.id,
            name=crit.name,
            description=crit.description,
            weight=float(crit.weight),
            direction=crit.direction,
            is_knockout=crit.is_knockout,
            data_type=crit.data_type,
        )
        db.add(criterion)

    await db.flush()

    # Audit trail
    await record_audit_event(
        db=db,
        rfq_id=rfq.id,
        event_type="rfq.created",
        actor_id=actor_id,
        payload={
            "title": rfq.title,
            "category": rfq.category,
            "currency": rfq.reference_currency,
            "line_items_count": len(rfq_in.line_items),
            "criteria_count": len(rfq_in.criteria),
        },
    )

    await db.commit()
    return await get_rfq_or_404(db, rfq.id)


async def get_rfq_or_404(db: AsyncSession, rfq_id: str) -> RFQ:
    """Fetch an RFQ by ID with line items and criteria loaded, or raise 404."""
    query = (
        select(RFQ)
        .where(RFQ.id == rfq_id)
        .options(
            selectinload(RFQ.line_items),
            selectinload(RFQ.criteria),
        )
    )
    result = await db.execute(query)
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RFQ with ID '{rfq_id}' not found",
        )
    return rfq


async def list_rfqs(
    db: AsyncSession,
    include_archived: bool = False,
    status_filter: RFQStatus | None = None,
    category: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[RFQ], int]:
    """List RFQs with filtering and total count."""
    query = select(RFQ).options(
        selectinload(RFQ.line_items),
        selectinload(RFQ.criteria),
    )

    if not include_archived:
        query = query.where(RFQ.is_archived.is_(False))

    if status_filter:
        query = query.where(RFQ.status == status_filter)

    if category:
        query = query.where(RFQ.category.ilike(f"%{category}%"))

    # Count total matching
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Paginate and order by newest first
    query = query.order_by(RFQ.created_at.desc()).offset(skip).limit(limit)
    items_result = await db.execute(query)
    rfqs = list(items_result.scalars().all())

    return rfqs, total


async def update_rfq(
    db: AsyncSession,
    rfq_id: str,
    update_data: RFQUpdate,
    actor_id: str = "system",
) -> RFQ:
    """Update general fields of an RFQ."""
    rfq = await get_rfq_or_404(db, rfq_id)

    changes = {}
    if update_data.title is not None and update_data.title != rfq.title:
        changes["title"] = {"old": rfq.title, "new": update_data.title}
        rfq.title = update_data.title

    if update_data.description is not None:
        rfq.description = update_data.description

    if update_data.category is not None:
        rfq.category = update_data.category

    if update_data.status is not None and update_data.status != rfq.status:
        changes["status"] = {"old": rfq.status.value, "new": update_data.status.value}
        rfq.status = update_data.status

    if update_data.reference_currency is not None:
        rfq.reference_currency = update_data.reference_currency.upper()

    if update_data.is_archived is not None and update_data.is_archived != rfq.is_archived:
        changes["is_archived"] = {"old": rfq.is_archived, "new": update_data.is_archived}
        rfq.is_archived = update_data.is_archived

    await record_audit_event(
        db=db,
        rfq_id=rfq.id,
        event_type="rfq.updated",
        actor_id=actor_id,
        payload=changes,
    )

    await db.commit()
    return await get_rfq_or_404(db, rfq_id)


async def archive_rfq(
    db: AsyncSession,
    rfq_id: str,
    actor_id: str = "system",
) -> RFQ:
    """Soft-delete an RFQ by setting is_archived=True and status=archived."""
    rfq = await get_rfq_or_404(db, rfq_id)
    rfq.is_archived = True
    rfq.status = RFQStatus.ARCHIVED

    await record_audit_event(
        db=db,
        rfq_id=rfq.id,
        event_type="rfq.archived",
        actor_id=actor_id,
        payload={"previous_status": rfq.status.value},
    )

    await db.commit()
    return await get_rfq_or_404(db, rfq_id)


async def unarchive_rfq(
    db: AsyncSession,
    rfq_id: str,
    actor_id: str = "system",
) -> RFQ:
    """Restore an archived RFQ back to active status."""
    rfq = await get_rfq_or_404(db, rfq_id)
    rfq.is_archived = False
    rfq.status = RFQStatus.ACTIVE

    await record_audit_event(
        db=db,
        rfq_id=rfq.id,
        event_type="rfq.unarchived",
        actor_id=actor_id,
    )

    await db.commit()
    return await get_rfq_or_404(db, rfq_id)


async def clone_rfq(
    db: AsyncSession,
    rfq_id: str,
    new_title: str | None = None,
    actor_id: str = "system",
) -> RFQ:
    """Duplicate an existing RFQ as a new draft template."""
    source_rfq = await get_rfq_or_404(db, rfq_id)

    title = new_title or f"{source_rfq.title} (Clone)"
    cloned_rfq = RFQ(
        title=title,
        description=source_rfq.description,
        category=source_rfq.category,
        status=RFQStatus.DRAFT,
        reference_currency=source_rfq.reference_currency,
        created_by=actor_id,
        is_archived=False,
    )
    db.add(cloned_rfq)
    await db.flush()

    for item in source_rfq.line_items:
        new_item = RFQLineItem(
            rfq_id=cloned_rfq.id,
            position=item.position,
            description=item.description,
            quantity=item.quantity,
            unit=item.unit,
        )
        db.add(new_item)

    for crit in source_rfq.criteria:
        new_crit = EvaluationCriterion(
            rfq_id=cloned_rfq.id,
            name=crit.name,
            description=crit.description,
            weight=crit.weight,
            direction=crit.direction,
            is_knockout=crit.is_knockout,
            data_type=crit.data_type,
        )
        db.add(new_crit)

    await db.flush()

    await record_audit_event(
        db=db,
        rfq_id=cloned_rfq.id,
        event_type="rfq.cloned",
        actor_id=actor_id,
        payload={"source_rfq_id": source_rfq.id, "source_title": source_rfq.title},
    )

    await db.commit()
    return await get_rfq_or_404(db, cloned_rfq.id)


async def update_criteria(
    db: AsyncSession,
    rfq_id: str,
    criteria_in: list[CriterionCreate],
    actor_id: str = "system",
) -> RFQ:
    """Replace and update all evaluation criteria with weight validation."""
    validate_criteria_weights(criteria_in)
    rfq = await get_rfq_or_404(db, rfq_id)

    # Clear existing criteria collection (cascade delete-orphan cleans DB)
    rfq.criteria.clear()
    await db.flush()

    # Add new criteria
    for crit in criteria_in:
        new_crit = EvaluationCriterion(
            rfq_id=rfq.id,
            name=crit.name,
            description=crit.description,
            weight=float(crit.weight),
            direction=crit.direction,
            is_knockout=crit.is_knockout,
            data_type=crit.data_type,
        )
        rfq.criteria.append(new_crit)

    await db.flush()

    await record_audit_event(
        db=db,
        rfq_id=rfq.id,
        event_type="rfq.criteria_updated",
        actor_id=actor_id,
        payload={"new_criteria_count": len(criteria_in)},
    )

    await db.commit()
    return await get_rfq_or_404(db, rfq_id)
