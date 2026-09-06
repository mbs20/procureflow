from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from procureflow.models.audit import AuditLog
from procureflow.models.rfq import (
    CriterionDirection,
    RFQStatus,
)
from procureflow.schemas.rfq import (
    CriterionCreate,
    LineItemCreate,
    RFQCreate,
    RFQUpdate,
)
from procureflow.services.rfq_service import (
    archive_rfq,
    clone_rfq,
    create_rfq,
    list_rfqs,
    unarchive_rfq,
    update_rfq,
    validate_criteria_weights,
)


def test_validate_criteria_weights():
    # Valid: 0.40 + 0.30 + 0.20 + 0.10 == 1.00
    valid_criteria = [
        CriterionCreate(name="Price", weight=Decimal("0.40")),
        CriterionCreate(name="Lead Time", weight=Decimal("0.30")),
        CriterionCreate(name="Quality", weight=Decimal("0.20")),
        CriterionCreate(name="Terms", weight=Decimal("0.10")),
    ]
    validate_criteria_weights(valid_criteria)

    # Invalid: 0.50 + 0.40 == 0.90 != 1.00
    invalid_criteria = [
        CriterionCreate(name="Price", weight=Decimal("0.50")),
        CriterionCreate(name="Lead Time", weight=Decimal("0.40")),
    ]
    with pytest.raises(HTTPException) as exc_info:
        validate_criteria_weights(invalid_criteria)
    assert exc_info.value.status_code == 422
    assert "must sum to 1.00" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_create_rfq_service(db_session: AsyncSession):
    rfq_in = RFQCreate(
        title="Industrial Butterfly Valves RFQ",
        description="Supply of ISO flanged butterfly valves",
        category="Valves",
        reference_currency="USD",
        line_items=[
            LineItemCreate(
                description="3-inch Butterfly Valve", quantity=Decimal("25"), unit="pcs"
            ),
            LineItemCreate(description="2-inch Ball Valve", quantity=Decimal("40"), unit="pcs"),
        ],
        criteria=[
            CriterionCreate(
                name="Price", weight=Decimal("0.60"), direction=CriterionDirection.LOWER_IS_BETTER
            ),
            CriterionCreate(
                name="Lead Time",
                weight=Decimal("0.40"),
                direction=CriterionDirection.LOWER_IS_BETTER,
            ),
        ],
    )

    created = await create_rfq(db=db_session, rfq_in=rfq_in, actor_id="buyer_alice")

    assert created.id is not None
    assert created.title == "Industrial Butterfly Valves RFQ"
    assert created.status == RFQStatus.DRAFT
    assert created.is_archived is False
    assert len(created.line_items) == 2
    assert len(created.criteria) == 2

    # Check audit log entry
    audit_res = await db_session.execute(
        select(AuditLog).where(AuditLog.rfq_id == created.id, AuditLog.event_type == "rfq.created")
    )
    audit_entry = audit_res.scalar_one_or_none()
    assert audit_entry is not None
    assert audit_entry.actor_id == "buyer_alice"
    assert audit_entry.payload["line_items_count"] == 2


@pytest.mark.asyncio
async def test_update_and_archive_rfq(db_session: AsyncSession):
    rfq_in = RFQCreate(
        title="Original Title",
        category="Piping",
        line_items=[],
        criteria=[],
    )
    rfq = await create_rfq(db=db_session, rfq_in=rfq_in, actor_id="buyer_alice")

    # Update
    updated = await update_rfq(
        db=db_session,
        rfq_id=rfq.id,
        update_data=RFQUpdate(title="Updated Title", status=RFQStatus.ACTIVE),
        actor_id="buyer_alice",
    )
    assert updated.title == "Updated Title"
    assert updated.status == RFQStatus.ACTIVE

    # Archive (soft delete)
    archived = await archive_rfq(db=db_session, rfq_id=rfq.id, actor_id="buyer_alice")
    assert archived.is_archived is True
    assert archived.status == RFQStatus.ARCHIVED

    # Test that default list excludes archived RFQs
    active_rfqs, total = await list_rfqs(db=db_session, include_archived=False)
    assert rfq.id not in [r.id for r in active_rfqs]

    # Test that include_archived=True returns it
    all_rfqs, total_all = await list_rfqs(db=db_session, include_archived=True)
    assert rfq.id in [r.id for r in all_rfqs]

    # Unarchive
    restored = await unarchive_rfq(db=db_session, rfq_id=rfq.id, actor_id="buyer_alice")
    assert restored.is_archived is False
    assert restored.status == RFQStatus.ACTIVE


@pytest.mark.asyncio
async def test_clone_rfq(db_session: AsyncSession):
    rfq_in = RFQCreate(
        title="Template RFQ - Stainless Pumps",
        category="Pumps",
        line_items=[
            LineItemCreate(description="Centrifugal Pump 5kW", quantity=Decimal("2"), unit="units"),
        ],
        criteria=[
            CriterionCreate(name="Cost", weight=Decimal("0.70")),
            CriterionCreate(name="Delivery", weight=Decimal("0.30")),
        ],
    )
    source = await create_rfq(db=db_session, rfq_in=rfq_in, actor_id="buyer_alice")

    cloned = await clone_rfq(
        db=db_session,
        rfq_id=source.id,
        new_title="2026 Q4 Pump Procurement",
        actor_id="buyer_bob",
    )

    assert cloned.id != source.id
    assert cloned.title == "2026 Q4 Pump Procurement"
    assert cloned.status == RFQStatus.DRAFT
    assert len(cloned.line_items) == 1
    assert cloned.line_items[0].description == "Centrifugal Pump 5kW"
    assert len(cloned.criteria) == 2
