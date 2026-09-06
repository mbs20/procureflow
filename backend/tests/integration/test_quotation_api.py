from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from procureflow.database import async_session_maker
from procureflow.models.extraction import ExtractedQuotation
from procureflow.tasks.extraction import extract_quotation_task

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "quotations"


@pytest.mark.asyncio
async def test_complete_quotation_ingestion_and_human_review(async_client: AsyncClient):
    headers = {"X-API-Key": "procureflow_dev_api_key_12345"}

    # 1. Create RFQ
    rfq_payload = {
        "title": "Industrial Bearings Procurement",
        "description": "Annual supply of precision bearings",
        "category": "Mechanical Components",
        "reference_currency": "USD",
        "line_items": [
            {
                "position": 1,
                "description": "Deep Groove Ball Bearings 6205-2RS",
                "quantity": 100,
                "unit": "pcs",
            }
        ],
        "criteria": [
            {"name": "Price", "weight": 0.60, "criterion_type": "price", "is_mandatory": True},
            {
                "name": "Lead Time",
                "weight": 0.40,
                "criterion_type": "lead_time",
                "is_mandatory": False,
            },
        ],
    }
    rfq_resp = await async_client.post("/api/v1/rfqs", json=rfq_payload, headers=headers)
    assert rfq_resp.status_code == 201, rfq_resp.text
    rfq_data = rfq_resp.json()
    rfq_id = rfq_data["id"]

    # 2. Create Quotation Container
    quote_payload = {
        "rfq_id": rfq_id,
        "supplier_name": "Apex Bearing Supply",
        "supplier_reference": "ABS-2026-01",
    }
    quote_resp = await async_client.post("/api/v1/quotations", json=quote_payload, headers=headers)
    assert quote_resp.status_code == 201
    quote = quote_resp.json()
    quotation_id = quote["id"]
    assert quote["status"] == "uploaded"

    # 3. Test legacy .xls rejection
    legacy_file_path = FIXTURES_DIR / "legacy_quote.xls"
    with open(legacy_file_path, "rb") as f:
        legacy_resp = await async_client.post(
            f"/api/v1/quotations/{quotation_id}/documents",
            files={"file": ("legacy_quote.xls", f.read(), "application/vnd.ms-excel")},
            headers=headers,
        )
    assert legacy_resp.status_code == 422
    assert "Legacy Excel (.xls) format is not supported for v0.1" in legacy_resp.json()["detail"]

    # 4. Upload valid CSV document
    csv_file_path = FIXTURES_DIR / "clean_bearings.csv"
    with open(csv_file_path, "rb") as f:
        csv_bytes = f.read()
        upload_resp = await async_client.post(
            f"/api/v1/quotations/{quotation_id}/documents",
            files={"file": ("clean_bearings.csv", csv_bytes, "text/csv")},
            headers=headers,
        )
    assert upload_resp.status_code == 201
    doc_data = upload_resp.json()
    doc_id = doc_data["id"]
    assert doc_data["filename"] == "clean_bearings.csv"

    # 5. Download original document
    dl_resp = await async_client.get(
        f"/api/v1/quotations/{quotation_id}/documents/{doc_id}/download",
        headers=headers,
    )
    assert dl_resp.status_code == 200
    assert dl_resp.content == csv_bytes

    # 6. Trigger extraction (Runs synchronously under CELERY_ALWAYS_EAGER=true)
    extract_resp = await async_client.post(
        f"/api/v1/quotations/{quotation_id}/extract",
        headers=headers,
    )
    assert extract_resp.status_code == 200

    # 7. Check quotation status: MUST transition to needs_review (NEVER approved automatically!)
    status_resp = await async_client.get(f"/api/v1/quotations/{quotation_id}", headers=headers)
    assert status_resp.status_code == 200
    updated_quote = status_resp.json()
    assert updated_quote["status"] == "needs_review"

    # 8. Idempotent re-extraction & extraction history check
    re_extract_resp = await async_client.post(
        f"/api/v1/quotations/{quotation_id}/extract",
        headers=headers,
    )
    assert re_extract_resp.status_code == 200

    # 9. Get latest extraction
    latest_resp = await async_client.get(
        f"/api/v1/quotations/{quotation_id}/extractions/latest",
        headers=headers,
    )
    assert latest_resp.status_code == 200
    extraction = latest_resp.json()
    assert extraction["is_current"] is True
    assert extraction["extraction_version"] == "2.0"  # Versioned after second run!
    assert len(extraction["line_items"]) == 3

    # Check evidence coordinates
    first_item = extraction["line_items"][0]
    assert first_item["source_bbox"] is not None
    assert first_item["source_bbox"]["type"] == "spreadsheet"
    assert first_item["source_bbox"]["row_idx"] == 2
    assert first_item["rfq_line_item_id"] is not None  # Auto-matched to RFQ line item!
    line_item_id = first_item["id"]

    # 10. Human-in-the-loop correction of extracted line item
    # Editing unit_price updates calculated_total_price without overwriting supplier quoted total_price
    correction_payload = {
        "unit_price": 11.95,
        "quantity": 100,
    }
    patch_resp = await async_client.patch(
        f"/api/v1/quotations/{quotation_id}/line-items/{line_item_id}",
        json=correction_payload,
        headers=headers,
    )
    assert patch_resp.status_code == 200
    corrected_item = patch_resp.json()
    assert float(corrected_item["unit_price"]) == 11.95
    # Preserves supplier quoted value (1250.00) rather than silently replacing it:
    assert float(corrected_item["total_price"]) == 1250.00
    # Calculates ProcureFlow total (100 * 11.95 = 1195.00):
    assert float(corrected_item["calculated_total_price"]) == 1195.00
    # Flags discrepancy between quoted and calculated:
    assert corrected_item["has_discrepancy"] is True
    assert corrected_item["human_corrected"] is True

    # When human explicitly supplies total_price, both are updated and discrepancy is resolved
    explicit_total_resp = await async_client.patch(
        f"/api/v1/quotations/{quotation_id}/line-items/{line_item_id}",
        json={"total_price": 1195.00},
        headers=headers,
    )
    assert explicit_total_resp.status_code == 200
    explicit_item = explicit_total_resp.json()
    assert float(explicit_item["total_price"]) == 1195.00
    assert float(explicit_item["calculated_total_price"]) == 1195.00
    assert explicit_item["has_discrepancy"] is False

    # 11. Human review decision (Approve quotation)
    approval_resp = await async_client.patch(
        f"/api/v1/quotations/{quotation_id}/status",
        json={"status": "approved"},
        headers=headers,
    )
    assert approval_resp.status_code == 200
    approved_quote = approval_resp.json()
    assert approved_quote["status"] == "approved"


@pytest.mark.asyncio
async def test_scanned_pdf_ocr_end_to_end(async_client: AsyncClient):
    """
    Prove scanned-PDF OCR end-to-end with genuine image-only PDF fixture:
    scanned PDF -> OCR triggered -> actual text recovered -> structured quotation fields produced -> OCR source evidence persisted.
    """
    headers = {"X-API-Key": "procureflow_dev_api_key_12345"}

    # 1. Create RFQ
    rfq_payload = {
        "title": "Hydraulic System Maintenance",
        "description": "Cylinder replacements",
        "category": "Hydraulics",
        "reference_currency": "USD",
        "line_items": [
            {
                "position": 1,
                "description": "Heavy Duty Hydraulic Cylinder 50mm bore",
                "quantity": 4,
                "unit": "units",
            }
        ],
        "criteria": [
            {"name": "Price", "weight": 1.0, "criterion_type": "price", "is_mandatory": True},
        ],
    }
    rfq_resp = await async_client.post("/api/v1/rfqs", json=rfq_payload, headers=headers)
    assert rfq_resp.status_code == 201
    rfq_id = rfq_resp.json()["id"]

    # 2. Create Quotation
    quote_resp = await async_client.post(
        "/api/v1/quotations",
        json={"rfq_id": rfq_id, "supplier_name": "Hydraulics Express"},
        headers=headers,
    )
    assert quote_resp.status_code == 201
    quotation_id = quote_resp.json()["id"]

    # 3. Upload genuinely scanned/image-only PDF fixture
    scanned_pdf_path = FIXTURES_DIR / "scanned_quote_image.pdf"
    with open(scanned_pdf_path, "rb") as f:
        pdf_bytes = f.read()
        upload_resp = await async_client.post(
            f"/api/v1/quotations/{quotation_id}/documents",
            files={"file": ("scanned_quote_image.pdf", pdf_bytes, "application/pdf")},
            headers=headers,
        )
    assert upload_resp.status_code == 201

    # 4. Trigger extraction pipeline
    extract_resp = await async_client.post(
        f"/api/v1/quotations/{quotation_id}/extract",
        headers=headers,
    )
    assert extract_resp.status_code == 200

    # 5. Verify quotation status is needs_review
    quote_check = await async_client.get(f"/api/v1/quotations/{quotation_id}", headers=headers)
    assert quote_check.json()["status"] == "needs_review"

    # 6. Verify extraction result, recovered text, and OCR source evidence
    latest_resp = await async_client.get(
        f"/api/v1/quotations/{quotation_id}/extractions/latest",
        headers=headers,
    )
    assert latest_resp.status_code == 200
    ext = latest_resp.json()
    assert ext["extraction_model"] == "ocr-assisted-pdf"
    assert len(ext["line_items"]) >= 1

    item = ext["line_items"][0]
    # Check text recovered from image via OCR
    assert "Hydraulic Cylinder" in item["description_raw"]
    assert float(item["quantity"]) == 4.0
    assert float(item["unit_price"]) == 320.0
    assert float(item["total_price"]) == 1280.0
    assert float(item["calculated_total_price"]) == 1280.0
    assert item["has_discrepancy"] is False

    # Check OCR source evidence
    evidence = item.get("source_evidence")
    assert evidence is not None
    assert evidence["type"] == "ocr_pdf"
    assert evidence["page"] == 1
    assert evidence["ocr_confidence"] >= 0.8
    assert "bbox" in evidence
    assert isinstance(evidence["bbox"], list)
    assert len(evidence["bbox"]) == 4
    # Check backward compatibility property
    assert item.get("source_bbox") == evidence


@pytest.mark.asyncio
async def test_extraction_versioning_and_retry_idempotency(async_client: AsyncClient):
    """
    Explicitly prove that:
    1. Extraction v1 is preserved after re-extraction;
    2. v1 becomes is_current=False;
    3. v2 becomes is_current=True;
    4. Exactly one extraction may be current for a quotation;
    5. Repeated/retried task execution cannot create uncontrolled duplicate current extraction sets.
    """
    headers = {"X-API-Key": "procureflow_dev_api_key_12345"}

    # Setup RFQ and Quotation
    rfq_resp = await async_client.post(
        "/api/v1/rfqs",
        json={
            "title": "Fastener Procurement",
            "category": "Fasteners",
            "reference_currency": "USD",
            "line_items": [
                {"position": 1, "description": "Bolt M8x40", "quantity": 50, "unit": "pcs"}
            ],
            "criteria": [
                {"name": "Price", "weight": 1.0, "criterion_type": "price", "is_mandatory": True}
            ],
        },
        headers=headers,
    )
    rfq_id = rfq_resp.json()["id"]

    quote_resp = await async_client.post(
        "/api/v1/quotations",
        json={"rfq_id": rfq_id, "supplier_name": "Fastener Direct"},
        headers=headers,
    )
    quotation_id = quote_resp.json()["id"]

    csv_path = FIXTURES_DIR / "clean_bearings.csv"
    with open(csv_path, "rb") as f:
        await async_client.post(
            f"/api/v1/quotations/{quotation_id}/documents",
            files={"file": ("clean_bearings.csv", f.read(), "text/csv")},
            headers=headers,
        )

    # First extraction -> v1
    v1_resp = await async_client.post(f"/api/v1/quotations/{quotation_id}/extract", headers=headers)
    assert v1_resp.status_code == 200

    # Query DB directly for all extractions of this quotation
    async with async_session_maker() as session:
        stmt = (
            select(ExtractedQuotation)
            .where(ExtractedQuotation.quotation_id == quotation_id)
            .order_by(ExtractedQuotation.extracted_at)
        )
        res = await session.execute(stmt)
        all_exts = list(res.scalars().all())
        assert len(all_exts) == 1
        v1 = all_exts[0]
        assert v1.is_current is True
        assert v1.extraction_version == "1.0"
        v1_id = v1.id

    # Second extraction (re-extraction) -> v2
    v2_resp = await async_client.post(f"/api/v1/quotations/{quotation_id}/extract", headers=headers)
    assert v2_resp.status_code == 200

    # Query DB again: v1 must be preserved and set to is_current=False; v2 must have is_current=True
    async with async_session_maker() as session:
        res = await session.execute(stmt)
        all_exts = list(res.scalars().all())
        assert len(all_exts) == 2

        # v1 preserved with is_current=False
        v1_found = next(e for e in all_exts if e.id == v1_id)
        assert v1_found.is_current is False
        assert v1_found.extraction_version == "1.0"

        # v2 is current
        v2_found = next(e for e in all_exts if e.id != v1_id)
        assert v2_found.is_current is True
        assert v2_found.extraction_version == "2.0"

        # Invariant: EXACTLY one extraction may be current for this quotation
        current_exts = [e for e in all_exts if e.is_current is True]
        assert len(current_exts) == 1

        # Invariant: Database level partial unique index prevents duplicate current extractions
        duplicate_current = ExtractedQuotation(
            quotation_id=quotation_id,
            extraction_model="test-dup",
            extraction_version="99.0",
            is_current=True,
        )
        session.add(duplicate_current)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

    # Retry idempotency: run Celery task multiple times sequentially
    res1 = extract_quotation_task(quotation_id)
    assert res1["status"] == "needs_review"
    res2 = extract_quotation_task(quotation_id)
    assert res2["status"] == "needs_review"

    # Invariant: At every point, exactly one extraction is current
    async with async_session_maker() as session:
        res = await session.execute(stmt)
        all_exts = list(res.scalars().all())
        current_exts = [e for e in all_exts if e.is_current is True]
        assert len(current_exts) == 1
        assert len(all_exts) == 4  # v1, v2, v3, v4 all preserved for audit/history
