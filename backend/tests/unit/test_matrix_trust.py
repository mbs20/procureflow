import pytest

from procureflow.models.extraction import ExtractedLineItem, ExtractedQuotation
from procureflow.models.normalization import NormalizationOverride
from procureflow.models.quotation import QuotationDocument, QuotationStatus, SupplierQuotation
from procureflow.models.rfq import RFQ, RFQLineItem
from procureflow.services.matrix_service import MatrixService


@pytest.mark.parametrize(
    "state,current,expected",
    [
        ("needs_review", True, 0),
        ("rejected", True, 0),
        ("approved", False, 0),
        ("approved", True, 1),
    ],
)
async def test_matrix_requires_approved_current_extraction(db_session, state, current, expected):
    rfq = RFQ(title="Trust boundary", reference_currency="USD")
    db_session.add(rfq)
    await db_session.flush()
    quote = SupplierQuotation(
        rfq_id=rfq.id, supplier_name="Supplier", status=QuotationStatus(state)
    )
    db_session.add(quote)
    await db_session.flush()
    db_session.add(ExtractedQuotation(quotation_id=quote.id, is_current=current))
    await db_session.commit()
    matrix = await MatrixService().compile_comparison_matrix(db_session, rfq.id)
    assert len(matrix.suppliers) == expected


async def test_matrix_uses_effective_line_lead_time_and_preserves_source(db_session):
    rfq = RFQ(title="Lead time traceability", reference_currency="USD")
    db_session.add(rfq)
    await db_session.flush()
    required = RFQLineItem(rfq_id=rfq.id, description="Bearing", quantity=1, unit="pcs")
    quote = SupplierQuotation(
        rfq_id=rfq.id, supplier_name="Supplier", status=QuotationStatus.APPROVED
    )
    db_session.add_all([required, quote])
    await db_session.flush()
    extraction = ExtractedQuotation(quotation_id=quote.id, is_current=True)
    document = QuotationDocument(
        quotation_id=quote.id,
        filename="quote.csv",
        storage_path="quote.csv",
        file_hash="a" * 64,
        mime_type="text/csv",
        size_bytes=1,
    )
    db_session.add_all([extraction, document])
    await db_session.flush()
    line = ExtractedLineItem(
        extracted_quotation_id=extraction.id,
        rfq_line_item_id=required.id,
        description_raw="Bearing",
        quantity=1,
        unit="pcs",
        unit_price=10,
        total_price=10,
        currency="USD",
        lead_time_days=14,
    )
    db_session.add(line)
    await db_session.flush()
    db_session.add(
        NormalizationOverride(
            rfq_id=rfq.id,
            quotation_id=quote.id,
            line_item_id=line.id,
            field_name="lead_time",
            original_value={"lead_time_days": 14},
            override_value={"lead_time_days": 8},
            override_reason="Confirmed delivery",
        )
    )
    await db_session.commit()
    matrix = await MatrixService().compile_comparison_matrix(db_session, rfq.id)
    assert matrix.suppliers[0].overall_lead_time_days == 8
    assert matrix.suppliers[0].overall_lead_time_original == "14 days"
    cell = matrix.required_line_items[0].supplier_cells[quote.id]
    assert cell.line_lead_time_original_days == 14
    assert cell.line_lead_time_days == 8
    assert cell.source_document_id == document.id
