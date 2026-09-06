import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from procureflow.models.rfq import (
    RFQ,
    CriterionDirection,
    EvaluationCriterion,
    RFQLineItem,
    RFQStatus,
)


@pytest.mark.asyncio
async def test_create_and_query_rfq_with_relationships(db_session: AsyncSession):
    # Test creating an RFQ with line items and criteria
    rfq = RFQ(
        title="Test Bearings & Motors",
        description="Supply of industrial bearings",
        category="Machinery",
        status=RFQStatus.DRAFT,
        reference_currency="EUR",
    )
    db_session.add(rfq)
    await db_session.flush()

    line_item = RFQLineItem(
        rfq_id=rfq.id,
        position=1,
        description="Precision Ball Bearing 6204",
        quantity=500.0,
        unit="pcs",
    )
    criterion = EvaluationCriterion(
        rfq_id=rfq.id,
        name="Unit Price",
        weight=0.60,
        direction=CriterionDirection.LOWER_IS_BETTER,
    )
    db_session.add(line_item)
    db_session.add(criterion)
    await db_session.commit()

    # Query back
    result = await db_session.execute(select(RFQ).where(RFQ.id == rfq.id))
    fetched_rfq = result.scalar_one()

    assert fetched_rfq.title == "Test Bearings & Motors"
    assert fetched_rfq.reference_currency == "EUR"
    assert fetched_rfq.is_archived is False
