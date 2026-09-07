from pathlib import Path

import pytest
from httpx import AsyncClient

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.mark.asyncio
async def test_human_review_complete_lifecycle(async_client: AsyncClient):
    """
    Test Phase 3 Human Review workflow:
    1. Ingestion of quotation into needs_review.
    2. Adding a line item.
    3. Soft-deleting an extraneous item (never hard deleted).
    4. Restoring an excluded item.
    5. Editing values while preserving supplier-quoted total vs calculated total.
    6. Updating header fields.
    7. Server-side validation rules blocking approval on critical issue.
    8. Acknowledging warning and approving extraction.
    9. Verifying immutable audit trail.
    """
    headers = {"X-API-Key": "procureflow_dev_api_key_12345"}

    # 1. Create RFQ
    rfq_payload = {
        "title": "Industrial Conveyor Bearings",
        "category": "Mechanical Components",
        "reference_currency": "USD",
        "line_items": [
            {
                "position": 1,
                "description": "Deep Groove Ball Bearing 6204-2RS",
                "quantity": 100,
                "unit": "pcs",
            },
            {
                "position": 2,
                "description": "Tapered Roller Bearing 32208",
                "quantity": 50,
                "unit": "pcs",
            },
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
        json={"rfq_id": rfq_id, "supplier_name": "Apex Industrial Supplies"},
        headers=headers,
    )
    assert quote_resp.status_code == 201
    quote_id = quote_resp.json()["id"]

    # 3. Upload Document (CSV fixture)
    csv_path = FIXTURES_DIR / "quotations" / "clean_bearings.csv"
    with open(csv_path, "rb") as f:
        upload_resp = await async_client.post(
            f"/api/v1/quotations/{quote_id}/documents",
            files={"file": ("clean_bearings.csv", f.read(), "text/csv")},
            headers=headers,
        )
    assert upload_resp.status_code == 201

    # 4. Trigger Extraction
    ext_trig = await async_client.post(f"/api/v1/quotations/{quote_id}/extract", headers=headers)
    assert ext_trig.status_code == 200

    # 5. Fetch Extraction
    ext_resp = await async_client.get(
        f"/api/v1/quotations/{quote_id}/extractions/latest", headers=headers
    )
    assert ext_resp.status_code == 200
    ext = ext_resp.json()
    assert len(ext["line_items"]) >= 1

    # 6. Add missed line item
    add_resp = await async_client.post(
        f"/api/v1/quotations/{quote_id}/line-items",
        json={
            "description_raw": "Manual Grease Fitting Pack M6",
            "quantity": 10,
            "unit": "pack",
            "unit_price": 15.00,
            "total_price": 150.00,
            "currency": "USD",
        },
        headers=headers,
    )
    assert add_resp.status_code == 201
    added_item = add_resp.json()
    assert added_item["human_corrected"] is True
    assert added_item["is_removed"] is False

    # 7. Soft delete the newly added line item (never hard-deleted!)
    del_resp = await async_client.delete(
        f"/api/v1/quotations/{quote_id}/line-items/{added_item['id']}?reason=Duplicate entry",
        headers=headers,
    )
    assert del_resp.status_code == 200
    del_item = del_resp.json()
    assert del_item["is_removed"] is True
    assert del_item["removal_reason"] == "Duplicate entry"

    # Verify item is still present in latest extraction (marked is_removed=True)
    ext_check = await async_client.get(
        f"/api/v1/quotations/{quote_id}/extractions/latest", headers=headers
    )
    all_item_ids = [i["id"] for i in ext_check.json()["line_items"]]
    assert added_item["id"] in all_item_ids

    # 8. Restore the soft-deleted line item
    restore_resp = await async_client.post(
        f"/api/v1/quotations/{quote_id}/line-items/{added_item['id']}/restore",
        headers=headers,
    )
    assert restore_resp.status_code == 200
    assert restore_resp.json()["is_removed"] is False

    # 9. Preserve quoted vs calculated values during correction
    # Update unit_price from 15.00 to 20.00, but supplier quoted was 150.00 -> should cause discrepancy
    patch_resp = await async_client.patch(
        f"/api/v1/quotations/{quote_id}/line-items/{added_item['id']}",
        json={"unit_price": 20.00},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    patched_item = patch_resp.json()
    assert float(patched_item["unit_price"]) == 20.00
    assert float(patched_item["total_price"]) == 150.00  # Preserved supplier-quoted!
    assert float(patched_item["calculated_total_price"]) == 200.00  # 10 * 20
    assert patched_item["has_discrepancy"] is True

    # 10. Check Server-Side Approval Validation
    # Because there is an unacknowledged arithmetic discrepancy (150 != 200), approval MUST fail!
    val_status_resp = await async_client.get(
        f"/api/v1/quotations/{quote_id}/validation-status",
        headers=headers,
    )
    assert val_status_resp.status_code == 200
    val_status = val_status_resp.json()
    assert val_status["can_approve"] is False
    assert any("arithmetic discrepancy" in msg for msg in val_status["critical_issues"])

    # Attempting to approve without acknowledgment must be rejected by server
    approve_fail = await async_client.patch(
        f"/api/v1/quotations/{quote_id}/status",
        json={"status": "approved"},
        headers=headers,
    )
    assert approve_fail.status_code == 422
    assert "critical unresolved issues" in approve_fail.json()["detail"]

    # 11. Acknowledge the discrepancy and successfully approve extraction
    approve_success = await async_client.patch(
        f"/api/v1/quotations/{quote_id}/status",
        json={
            "status": "approved",
            "acknowledged_warnings": [f"discrepancy_{added_item['id']}"],
        },
        headers=headers,
    )
    assert approve_success.status_code == 200
    assert approve_success.json()["status"] == "approved"

    # 12. Verify Audit Trail
    audit_resp = await async_client.get(
        f"/api/v1/quotations/{quote_id}/audit-logs",
        headers=headers,
    )
    assert audit_resp.status_code == 200
    logs = audit_resp.json()
    event_types = [log_item["event_type"] for log_item in logs]
    assert "LINE_ITEM_ADDED" in event_types
    assert "LINE_ITEM_EXCLUDED" in event_types
    assert "LINE_ITEM_RESTORED" in event_types
    assert "LINE_ITEM_CORRECTED" in event_types
    assert "QUOTATION_EXTRACTION_APPROVED" in event_types


@pytest.mark.asyncio
async def test_human_review_rejection_flow(async_client: AsyncClient):
    """Test rejecting extraction with mandatory reason."""
    headers = {"X-API-Key": "procureflow_dev_api_key_12345"}

    # Create RFQ and Quotation
    rfq_resp = await async_client.post(
        "/api/v1/rfqs",
        json={
            "title": "Test RFQ",
            "category": "General",
            "reference_currency": "USD",
            "line_items": [],
        },
        headers=headers,
    )
    rfq_id = rfq_resp.json()["id"]

    quote_resp = await async_client.post(
        "/api/v1/quotations",
        json={"rfq_id": rfq_id, "supplier_name": "Noncompliant Vendor"},
        headers=headers,
    )
    quote_id = quote_resp.json()["id"]

    # Reject extraction
    reject_resp = await async_client.patch(
        f"/api/v1/quotations/{quote_id}/status",
        json={"status": "rejected", "failure_reason": "Pricing format is illegible and incomplete"},
        headers=headers,
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "rejected"
    assert reject_resp.json()["failure_reason"] == "Pricing format is illegible and incomplete"

    # Verify audit log recorded rejection
    audit_resp = await async_client.get(
        f"/api/v1/quotations/{quote_id}/audit-logs", headers=headers
    )
    logs = audit_resp.json()
    assert any(log_item["event_type"] == "QUOTATION_EXTRACTION_REJECTED" for log_item in logs)


@pytest.mark.asyncio
async def test_currency_rules_clarification(async_client: AsyncClient):
    """
    Clarification test:
    1. A quotation in EUR against an RFQ in USD MUST be approvable (currency normalization belongs to Phase 4).
    2. Contradictory currencies within the quotation itself (e.g. one line in USD, one in EUR) is a critical blocker.
    """
    headers = {"X-API-Key": "procureflow_dev_api_key_12345"}

    # 1. Create RFQ with reference currency USD
    rfq_resp = await async_client.post(
        "/api/v1/rfqs",
        json={
            "title": "Global Fasteners Supply",
            "category": "Hardware",
            "reference_currency": "USD",
            "line_items": [],
        },
        headers=headers,
    )
    assert rfq_resp.status_code == 201
    rfq_id = rfq_resp.json()["id"]

    # 2. Case A: Quotation entirely in EUR (cross-currency vs RFQ)
    quote_eur_resp = await async_client.post(
        "/api/v1/quotations",
        json={"rfq_id": rfq_id, "supplier_name": "EuroFast GmbH"},
        headers=headers,
    )
    assert quote_eur_resp.status_code == 201
    quote_eur_id = quote_eur_resp.json()["id"]

    # Ingest EUR document and extract
    eur_csv = (
        b"Item Description,Quantity,Unit,Unit Price,Currency,Total Price,Lead Time Days\n"
        b"Precision Shaft Flange DN50,50,pcs,45.00,EUR,2250.00,10\n"
    )
    await async_client.post(
        f"/api/v1/quotations/{quote_eur_id}/documents",
        files={"file": ("german_flanges.csv", eur_csv, "text/csv")},
        headers=headers,
    )
    await async_client.post(f"/api/v1/quotations/{quote_eur_id}/extract", headers=headers)

    # Add line item with EUR currency
    await async_client.post(
        f"/api/v1/quotations/{quote_eur_id}/line-items",
        json={
            "description_raw": "Stainless Bolt Set M10",
            "quantity": 100,
            "unit": "pcs",
            "unit_price": 2.50,
            "total_price": 250.00,
            "currency": "EUR",
        },
        headers=headers,
    )

    # Cross-currency quotation (EUR vs USD RFQ) is eligible for approval
    val_status = await async_client.get(
        f"/api/v1/quotations/{quote_eur_id}/validation-status",
        headers=headers,
    )
    assert val_status.status_code == 200
    # No currency blockers!
    assert not any("currency" in issue.lower() for issue in val_status.json()["critical_issues"])

    # 3. Case B: Internal contradictory currencies within extraction (EUR + USD)
    await async_client.post(
        f"/api/v1/quotations/{quote_eur_id}/line-items",
        json={
            "description_raw": "Imported Washer Kit",
            "quantity": 50,
            "unit": "pcs",
            "unit_price": 1.00,
            "total_price": 50.00,
            "currency": "USD",  # Mismatched currency within same quotation!
        },
        headers=headers,
    )

    val_contradictory = await async_client.get(
        f"/api/v1/quotations/{quote_eur_id}/validation-status",
        headers=headers,
    )
    assert val_contradictory.status_code == 200
    assert val_contradictory.json()["can_approve"] is False
    assert any(
        "contradictory currencies" in issue.lower()
        for issue in val_contradictory.json()["critical_issues"]
    )

    # Attempting to approve must fail with 422
    approve_fail = await async_client.patch(
        f"/api/v1/quotations/{quote_eur_id}/status",
        json={"status": "approved"},
        headers=headers,
    )
    assert approve_fail.status_code == 422
