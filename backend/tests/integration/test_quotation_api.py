from pathlib import Path

import pytest
from httpx import AsyncClient

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
    assert float(corrected_item["total_price"]) == 1195.00
    assert corrected_item["human_corrected"] is True

    # 11. Human review decision (Approve quotation)
    approval_resp = await async_client.patch(
        f"/api/v1/quotations/{quotation_id}/status",
        json={"status": "approved"},
        headers=headers,
    )
    assert approval_resp.status_code == 200
    approved_quote = approval_resp.json()
    assert approved_quote["status"] == "approved"
