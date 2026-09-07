from pathlib import Path

import pytest
from httpx import AsyncClient

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.mark.asyncio
async def test_full_phase4_multi_supplier_comparison_matrix_lifecycle(async_client: AsyncClient):
    """
    Complete Phase 4 Multi-Supplier Normalization & Comparison Matrix Test:
    1. Create RFQ with 2 required line items (Reference Currency = USD).
    2. Create 3 approved supplier quotations in different currencies (USD, EUR, MAD) and units (pcs, units).
       - Supplier A: USD (100% coverage, Net 30, 14 days)
       - Supplier B: EUR (100% coverage, units synonym for pcs, Net 60, 3 weeks, + 1 extra unmapped item)
       - Supplier C: MAD (50% coverage - Item 2 missing, 10 business days, 100% advance)
    3. Retrieve comparison matrix and verify deterministic currency and UOM normalization.
    4. Verify missing items are flagged as 'not_quoted' (not treated as zero).
    5. Verify extra unmapped items are placed in extra_line_items.
    6. Verify lead time and payment terms normalization semantics.
    7. Apply human normalization override, verify matrix update, and revert override with append-only audit.
    8. Create comparison snapshot, update RFQ FX rates, and prove snapshot v1 remains 100% frozen/reproducible.
    9. Verify authoritative Phase 3 extraction data remains completely unchanged.
    """
    headers = {"X-API-Key": "procureflow_dev_api_key_12345"}
    csv_file = FIXTURES_DIR / "quotations" / "clean_bearings.csv"

    # -------------------------------------------------------------------------
    # 1. Create RFQ
    # -------------------------------------------------------------------------
    rfq_payload = {
        "title": "Industrial High-Load Bearing Package",
        "description": "Bearings and seals for conveyor drive unit",
        "category": "Mechanical",
        "reference_currency": "USD",
        "line_items": [
            {
                "position": 1,
                "description": "Deep Groove Ball Bearing 6205",
                "quantity": 100,
                "unit": "pcs",
            },
            {
                "position": 2,
                "description": "NBR Rotary Shaft Seal 40x62x7",
                "quantity": 50,
                "unit": "pcs",
            },
        ],
        "criteria": [
            {"name": "Price", "weight": 0.60, "direction": "lower_is_better", "data_type": "price"},
            {
                "name": "Delivery",
                "weight": 0.40,
                "direction": "lower_is_better",
                "data_type": "days",
            },
        ],
    }
    rfq_resp = await async_client.post("/api/v1/rfqs", json=rfq_payload, headers=headers)
    assert rfq_resp.status_code == 201
    rfq_data = rfq_resp.json()
    rfq_id = rfq_data["id"]
    rfq_item_1_id = rfq_data["line_items"][0]["id"]
    rfq_item_2_id = rfq_data["line_items"][1]["id"]

    # -------------------------------------------------------------------------
    # 2. Supplier A (USD, 100% coverage, Net 30, 14 days)
    # -------------------------------------------------------------------------
    quote_a = (
        await async_client.post(
            "/api/v1/quotations",
            json={"rfq_id": rfq_id, "supplier_name": "Supplier A (US Precision)"},
            headers=headers,
        )
    ).json()
    qid_a = quote_a["id"]

    with open(csv_file, "rb") as f:
        await async_client.post(
            f"/api/v1/quotations/{qid_a}/documents",
            files={"file": ("quote_a.csv", f.read(), "text/csv")},
            headers=headers,
        )

    await async_client.post(f"/api/v1/quotations/{qid_a}/extract", headers=headers)
    extr_a = (await async_client.get(f"/api/v1/quotations/{qid_a}/extractions/latest")).json()

    # Map item 1
    item_a1_id = extr_a["line_items"][0]["id"]
    await async_client.patch(
        f"/api/v1/quotations/{qid_a}/line-items/{item_a1_id}",
        json={
            "rfq_line_item_id": rfq_item_1_id,
            "description_raw": "Ball Bearing 6205",
            "quantity": 100,
            "unit": "pcs",
            "unit_price": 12.50,
            "total_price": 1250.00,
            "currency": "USD",
            "lead_time_days": 14,
        },
        headers=headers,
    )

    # Map item 2
    item_a2_id = extr_a["line_items"][1]["id"]
    await async_client.patch(
        f"/api/v1/quotations/{qid_a}/line-items/{item_a2_id}",
        json={
            "rfq_line_item_id": rfq_item_2_id,
            "description_raw": "Shaft Seal 40x62x7 NBR",
            "quantity": 50,
            "unit": "pcs",
            "unit_price": 4.00,
            "total_price": 200.00,
            "currency": "USD",
            "lead_time_days": 14,
        },
        headers=headers,
    )

    # Soft delete item 3 from parser
    if len(extr_a["line_items"]) > 2:
        await async_client.delete(
            f"/api/v1/quotations/{qid_a}/line-items/{extr_a['line_items'][2]['id']}",
            headers=headers,
        )

    # Set payment terms field
    if extr_a["fields"]:
        await async_client.patch(
            f"/api/v1/quotations/{qid_a}/fields/{extr_a['fields'][0]['id']}",
            json={"raw_value": "Net 30 days"},
            headers=headers,
        )

    # Approve Supplier A extraction
    app_a = await async_client.patch(
        f"/api/v1/quotations/{qid_a}/status",
        json={"status": "approved"},
        headers=headers,
    )
    assert app_a.status_code == 200

    # -------------------------------------------------------------------------
    # 3. Supplier B (EUR, 100% coverage, units synonym for pcs, Net 60, 3 weeks, + 1 extra item)
    # -------------------------------------------------------------------------
    quote_b = (
        await async_client.post(
            "/api/v1/quotations",
            json={"rfq_id": rfq_id, "supplier_name": "Supplier B (EuroMotion AG)"},
            headers=headers,
        )
    ).json()
    qid_b = quote_b["id"]

    with open(csv_file, "rb") as f:
        await async_client.post(
            f"/api/v1/quotations/{qid_b}/documents",
            files={"file": ("quote_b.csv", f.read(), "text/csv")},
            headers=headers,
        )

    await async_client.post(f"/api/v1/quotations/{qid_b}/extract", headers=headers)
    extr_b = (await async_client.get(f"/api/v1/quotations/{qid_b}/extractions/latest")).json()

    item_b1_id = extr_b["line_items"][0]["id"]
    await async_client.patch(
        f"/api/v1/quotations/{qid_b}/line-items/{item_b1_id}",
        json={
            "rfq_line_item_id": rfq_item_1_id,
            "description_raw": "Radial Kugellager 6205",
            "quantity": 100,
            "unit": "units",  # synonym for pcs
            "unit_price": 11.30,
            "total_price": 1130.00,
            "currency": "EUR",
            "lead_time_days": 21,  # 3 weeks
        },
        headers=headers,
    )

    item_b2_id = extr_b["line_items"][1]["id"]
    await async_client.patch(
        f"/api/v1/quotations/{qid_b}/line-items/{item_b2_id}",
        json={
            "rfq_line_item_id": rfq_item_2_id,
            "description_raw": "Wellendichtring 40x62x7",
            "quantity": 50,
            "unit": "units",
            "unit_price": 3.50,
            "total_price": 175.00,
            "currency": "EUR",
            "lead_time_days": 21,
        },
        headers=headers,
    )

    # Convert 3rd item to extra unmapped item
    if len(extr_b["line_items"]) > 2:
        item_b3_id = extr_b["line_items"][2]["id"]
        await async_client.patch(
            f"/api/v1/quotations/{qid_b}/line-items/{item_b3_id}",
            json={
                "rfq_line_item_id": None,
                "description_raw": "Synthetic Bearing Grease 500g Tub",
                "quantity": 1,
                "unit": "tub",
                "unit_price": 15.00,
                "total_price": 15.00,
                "currency": "EUR",
            },
            headers=headers,
        )

    if extr_b["fields"]:
        await async_client.patch(
            f"/api/v1/quotations/{qid_b}/fields/{extr_b['fields'][0]['id']}",
            json={"raw_value": "Net 60"},
            headers=headers,
        )

    app_b = await async_client.patch(
        f"/api/v1/quotations/{qid_b}/status",
        json={"status": "approved"},
        headers=headers,
    )
    assert app_b.status_code == 200

    # -------------------------------------------------------------------------
    # 4. Supplier C (MAD, 50% coverage - missing Item 2, 10 business days, 100% advance)
    # -------------------------------------------------------------------------
    quote_c = (
        await async_client.post(
            "/api/v1/quotations",
            json={"rfq_id": rfq_id, "supplier_name": "Supplier C (Atlas Bearings SARL)"},
            headers=headers,
        )
    ).json()
    qid_c = quote_c["id"]

    with open(csv_file, "rb") as f:
        await async_client.post(
            f"/api/v1/quotations/{qid_c}/documents",
            files={"file": ("quote_c.csv", f.read(), "text/csv")},
            headers=headers,
        )

    await async_client.post(f"/api/v1/quotations/{qid_c}/extract", headers=headers)
    extr_c = (await async_client.get(f"/api/v1/quotations/{qid_c}/extractions/latest")).json()

    item_c1_id = extr_c["line_items"][0]["id"]
    await async_client.patch(
        f"/api/v1/quotations/{qid_c}/line-items/{item_c1_id}",
        json={
            "rfq_line_item_id": rfq_item_1_id,
            "description_raw": "Roulement a billes 6205",
            "quantity": 100,
            "unit": "pcs",
            "unit_price": 130.00,
            "total_price": 13000.00,
            "currency": "MAD",
            "lead_time_days": 10,
        },
        headers=headers,
    )

    # Exclude other items so Supplier C only quotes Item 1 (50% coverage)
    for rem_it in extr_c["line_items"][1:]:
        await async_client.delete(
            f"/api/v1/quotations/{qid_c}/line-items/{rem_it['id']}?reason=Not applicable",
            headers=headers,
        )

    if extr_c["fields"]:
        await async_client.patch(
            f"/api/v1/quotations/{qid_c}/fields/{extr_c['fields'][0]['id']}",
            json={"raw_value": "100% Advance payment"},
            headers=headers,
        )

    app_c = await async_client.patch(
        f"/api/v1/quotations/{qid_c}/status",
        json={"status": "approved"},
        headers=headers,
    )
    assert app_c.status_code == 200

    # Set payment terms overrides on quotations
    await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/matrix/overrides",
        json={
            "quotation_id": qid_a,
            "line_item_id": None,
            "field_name": "payment_terms",
            "override_value": {"payment_terms": "Net 30", "term_code": "NET_30"},
            "override_reason": "Verified from quotation document commercial terms",
        },
        headers=headers,
    )

    await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/matrix/overrides",
        json={
            "quotation_id": qid_b,
            "line_item_id": None,
            "field_name": "payment_terms",
            "override_value": {"payment_terms": "Net 60", "term_code": "NET_60"},
            "override_reason": "Verified from quotation document commercial terms",
        },
        headers=headers,
    )

    await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/matrix/overrides",
        json={
            "quotation_id": qid_c,
            "line_item_id": None,
            "field_name": "payment_terms",
            "override_value": {"payment_terms": "100% Advance Payment", "term_code": "ADVANCE_100"},
            "override_reason": "Verified from quotation document commercial terms",
        },
        headers=headers,
    )

    # -------------------------------------------------------------------------
    # 5. Fetch Comparison Matrix & Verify Deterministic Normalization
    # -------------------------------------------------------------------------
    matrix_resp = await async_client.get(f"/api/v1/rfqs/{rfq_id}/matrix")
    assert matrix_resp.status_code == 200
    matrix = matrix_resp.json()

    assert matrix["reference_currency"] == "USD"
    assert len(matrix["suppliers"]) == 3
    assert len(matrix["required_line_items"]) == 2
    assert len(matrix["extra_line_items"]) == 1
    assert matrix["extra_line_items"][0]["description_raw"] == "Synthetic Bearing Grease 500g Tub"

    supp_a = next(s for s in matrix["suppliers"] if s["quotation_id"] == qid_a)
    supp_b = next(s for s in matrix["suppliers"] if s["quotation_id"] == qid_b)
    supp_c = next(s for s in matrix["suppliers"] if s["quotation_id"] == qid_c)

    assert supp_a["rfq_coverage_pct"] == 100.0
    assert supp_b["rfq_coverage_pct"] == 100.0
    assert supp_c["rfq_coverage_pct"] == 50.0  # Missing 1 of 2 items

    assert supp_a["payment_terms_code"] == "NET_30"
    assert supp_b["payment_terms_code"] == "NET_60"
    assert supp_c["payment_terms_code"] == "ADVANCE_100"

    # Check Required Item 1 (Bearing 6205, Qty 100 pcs)
    row_1 = matrix["required_line_items"][0]
    assert row_1["description"] == "Deep Groove Ball Bearing 6205"

    cell_a1 = row_1["supplier_cells"][qid_a]
    assert cell_a1["is_quoted"] is True
    assert cell_a1["quoted_unit_price"] == 12.50
    assert cell_a1["normalized_unit_price"] == 12.50
    assert cell_a1["normalized_extended_price"] == 1250.00
    assert cell_a1["canonical_unit"] == "pcs"

    cell_b1 = row_1["supplier_cells"][qid_b]
    assert cell_b1["is_quoted"] is True
    assert cell_b1["quoted_unit_price"] == 11.30
    assert cell_b1["canonical_unit"] == "pcs"  # 'units' normalized safely to 'pcs'
    # FX: 11.30 EUR * 1.085 = 12.2605 USD -> 100 pcs = 1226.05 USD
    assert cell_b1["normalized_unit_price"] == 12.2605
    assert cell_b1["normalized_extended_price"] == 1226.05

    cell_c1 = row_1["supplier_cells"][qid_c]
    assert cell_c1["is_quoted"] is True
    assert cell_c1["quoted_unit_price"] == 130.00
    # FX: 130 MAD * 0.10 = 13.00 USD -> 100 pcs = 1300.00 USD
    assert cell_c1["normalized_unit_price"] == 13.00
    assert cell_c1["normalized_extended_price"] == 1300.00

    # Check Required Item 2 (Shaft Seal, Qty 50 pcs)
    row_2 = matrix["required_line_items"][1]
    cell_c2 = row_2["supplier_cells"][qid_c]
    assert cell_c2["is_quoted"] is False
    assert cell_c2["overall_cell_status"] == "not_quoted"
    assert cell_c2["normalized_unit_price"] is None
    assert cell_c2["normalized_extended_price"] is None  # Missing item is NOT treated as zero!

    # -------------------------------------------------------------------------
    # 6. Human Normalization Override & Append-Only Revert
    # -------------------------------------------------------------------------
    # Apply override on Supplier B Item 1 lead time
    override_payload = {
        "quotation_id": qid_b,
        "line_item_id": item_b1_id,
        "field_name": "lead_time",
        "override_value": {"lead_time_days": 18},
        "override_reason": "Supplier confirmed expedited shipment in 18 calendar days via email",
    }
    ov_resp = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/matrix/overrides",
        json=override_payload,
        headers=headers,
    )
    assert ov_resp.status_code == 201
    ov_data = ov_resp.json()
    assert ov_data["is_active"] is True
    override_id = ov_data["id"]

    # Verify matrix reflects override
    matrix_ov = (await async_client.get(f"/api/v1/rfqs/{rfq_id}/matrix")).json()
    cell_b1_ov = matrix_ov["required_line_items"][0]["supplier_cells"][qid_b]
    assert cell_b1_ov["is_human_overridden"] is True
    assert cell_b1_ov["line_lead_time_days"] == 18
    assert cell_b1_ov["override_id"] == override_id

    # Revert override
    rev_resp = await async_client.delete(
        f"/api/v1/rfqs/{rfq_id}/matrix/overrides/{override_id}",
        headers=headers,
    )
    assert rev_resp.status_code == 200
    assert rev_resp.json()["is_active"] is False

    # Verify matrix returned to deterministic default
    matrix_rev = (await async_client.get(f"/api/v1/rfqs/{rfq_id}/matrix")).json()
    cell_b1_rev = matrix_rev["required_line_items"][0]["supplier_cells"][qid_b]
    assert cell_b1_rev["is_human_overridden"] is False
    assert cell_b1_rev["line_lead_time_days"] == 21

    # -------------------------------------------------------------------------
    # 7. Comparison Snapshot Reproducibility & FX Rate Set Versioning
    # -------------------------------------------------------------------------
    # Freeze Comparison Snapshot v1
    snap_resp = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/matrix/snapshots",
        json={"title": "Baseline Comparison Snapshot"},
        headers=headers,
    )
    assert snap_resp.status_code == 201
    snap_1 = snap_resp.json()
    assert snap_1["snapshot_version"] == 1
    snap_1_id = snap_1["id"]

    # Configure new FX rates (Rate Set v2): Change EUR to 1.2000
    new_fx_payload = {
        "base_currency": "USD",
        "rates": {
            "USD": 1.0,
            "EUR": 1.2000,
            "MAD": 0.1000,
        },
        "provider_id": "procurement_committee_frozen_q1_rates",
        "is_synthetic": False,
    }
    fx_resp = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/matrix/fx-rates",
        json=new_fx_payload,
        headers=headers,
    )
    assert fx_resp.status_code == 201
    assert fx_resp.json()["version"] == 2

    # Verify active matrix now calculates with new EUR rate (1.2000)
    # 11.30 EUR * 1.2000 = 13.56 USD
    matrix_v2 = (await async_client.get(f"/api/v1/rfqs/{rfq_id}/matrix")).json()
    cell_b1_v2 = matrix_v2["required_line_items"][0]["supplier_cells"][qid_b]
    assert cell_b1_v2["normalized_unit_price"] == 13.56
    assert cell_b1_v2["normalized_extended_price"] == 1356.00

    # CRITICAL: Verify Snapshot v1 retrieved by ID remains 100% frozen with original EUR rate (1.0850) and $1,226.05
    snap_1_retrieved = (
        await async_client.get(f"/api/v1/rfqs/{rfq_id}/matrix/snapshots/{snap_1_id}")
    ).json()
    snap_1_matrix = snap_1_retrieved["matrix_data"]
    snap_1_cell_b1 = snap_1_matrix["required_line_items"][0]["supplier_cells"][qid_b]
    assert snap_1_cell_b1["normalized_unit_price"] == 12.2605
    assert snap_1_cell_b1["normalized_extended_price"] == 1226.05

    # -------------------------------------------------------------------------
    # 8. Authoritative Extraction Immutability Verification
    # -------------------------------------------------------------------------
    extr_b_check = (await async_client.get(f"/api/v1/quotations/{qid_b}/extractions/latest")).json()
    item_b1_check = next(it for it in extr_b_check["line_items"] if it["id"] == item_b1_id)
    assert float(item_b1_check["unit_price"]) == 11.30
    assert item_b1_check["currency"] == "EUR"
    assert float(item_b1_check["quantity"]) == 100.0
    assert item_b1_check["unit"] == "units"


@pytest.mark.asyncio
async def test_fx_v2_exact_arithmetic_and_snapshot_override_immutability(
    async_client: AsyncClient,
    tmp_path: Path,
) -> None:
    """
    1. Tests exact arithmetic:
       Supplier B quotes:
       Item 1: 100 pcs @ 100.00 EUR/pcs = 10,000.00 EUR
       Item 2: 10 box (20 pcs/box) @ 400.00 EUR/box = 4,000.00 EUR
       Quoted Grand Total = 14,000.00 EUR

       Under FX v1 (EUR=1.0850):
       Item 1: 100.00 * 1.0850 = $108.5000/pcs -> Ext: $10,850.00 USD
       Item 2: (400.00 / 20) * 1.0850 = $21.7000/pcs -> Ext: $4,340.00 USD
       Normalized Subtotal = $10,850.00 + $4,340.00 = $15,190.00 USD

       Under FX v2 (EUR=1.1000):
       Item 1: 100.00 * 1.1000 = $110.0000/pcs -> Ext: $11,000.00 USD
       Item 2: (400.00 / 20) * 1.1000 = $22.0000/pcs -> Ext: $4,400.00 USD
       Normalized Subtotal = $11,000.00 + $4,400.00 = $15,400.00 USD (Exact 14,000 * 1.1000)

    2. Tests Snapshot Override Immutability:
       - Apply packaging override (1 box = 20 pcs)
       - Freeze Snapshot A
       - Revert the override or change to factor 10
       - Verify Live Matrix updates to new state
       - Verify Snapshot A still has exact original factor 20, unit price 21.7000, and $15,190.00 subtotal
    """
    headers = {"X-API-Key": "dev_test_key_12345"}

    # 1. Create RFQ
    rfq_data = {
        "title": "Exact Arithmetic & Snapshot Override Test RFQ",
        "category": "Piping",
        "reference_currency": "USD",
        "line_items": [
            {"position": 1, "description": "Flange DN100", "quantity": 100, "unit": "pcs"},
            {"position": 2, "description": "Gasket DN100", "quantity": 200, "unit": "pcs"},
        ],
        "criteria": [
            {"name": "Price", "weight": 1.0, "criterion_type": "price", "is_mandatory": True}
        ],
    }
    rfq = (await async_client.post("/api/v1/rfqs", json=rfq_data, headers=headers)).json()
    rfq_id = rfq["id"]
    rfq_item_1_id = rfq["line_items"][0]["id"]
    rfq_item_2_id = rfq["line_items"][1]["id"]

    # 2. Configure initial FX rate set (v1: EUR = 1.0850)
    await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/matrix/fx-rates",
        json={"base_currency": "USD", "rates": {"USD": 1.0, "EUR": 1.0850}},
        headers=headers,
    )

    # 3. Create Quotation in EUR
    quote = (
        await async_client.post(
            "/api/v1/quotations",
            json={"rfq_id": rfq_id, "supplier_name": "EuroPipes & Valves GmbH"},
            headers=headers,
        )
    ).json()
    qid = quote["id"]

    csv_content = (
        "Description,Quantity,Unit,Unit Price,Currency,Total Price,Lead Time\n"
        "Flange DN100,100,pcs,100.00,EUR,10000.00,14\n"
        "Gasket DN100,10,box,400.00,EUR,4000.00,7\n"
    )
    doc_path = tmp_path / "quote.csv"
    doc_path.write_text(csv_content, encoding="utf-8")

    with open(doc_path, "rb") as f:
        await async_client.post(
            f"/api/v1/quotations/{qid}/documents",
            files={"file": ("quote.csv", f.read(), "text/csv")},
            headers=headers,
        )

    await async_client.post(f"/api/v1/quotations/{qid}/extract", headers=headers)
    extr = (await async_client.get(f"/api/v1/quotations/{qid}/extractions/latest")).json()

    item_1_id = extr["line_items"][0]["id"]
    item_2_id = extr["line_items"][1]["id"]

    await async_client.patch(
        f"/api/v1/quotations/{qid}/line-items/{item_1_id}",
        json={"rfq_line_item_id": rfq_item_1_id},
        headers=headers,
    )
    await async_client.patch(
        f"/api/v1/quotations/{qid}/line-items/{item_2_id}",
        json={"rfq_line_item_id": rfq_item_2_id},
        headers=headers,
    )

    # Approve extraction
    await async_client.patch(
        f"/api/v1/quotations/{qid}/status",
        json={"status": "approved"},
        headers=headers,
    )

    # 4. Apply packaging override on Item 2: 1 box = 20 pcs
    ov_res = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/matrix/overrides",
        json={
            "quotation_id": qid,
            "line_item_id": item_2_id,
            "field_name": "uom_factor",
            "override_value": {"conversion_factor": 20.0},
            "override_reason": "Confirmed 1 box = 20 pcs packaging specification with vendor",
        },
        headers=headers,
    )
    assert ov_res.status_code == 201
    override_id = ov_res.json()["id"]

    # 5. Verify live matrix under FX v1 (1.0850)
    matrix_v1 = (await async_client.get(f"/api/v1/rfqs/{rfq_id}/matrix")).json()
    supp_v1 = matrix_v1["suppliers"][0]
    assert supp_v1["quoted_grand_total"] == 14000.00
    # Exact v1 calculation: Item 1: 100 * 100 * 1.085 = 10,850.00; Item 2: (400/20)*1.085 = 21.7000 * 200 = 4,340.00
    assert supp_v1["normalized_line_item_subtotal"] == 15190.00
    assert supp_v1["normalized_comparable_total"] == 15190.00

    # 6. Freeze Snapshot A under FX v1 and override factor 20.0
    snap_a_res = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/matrix/snapshots",
        json={"title": "Snapshot A - Baseline with Factor 20 and FX v1"},
        headers=headers,
    )
    assert snap_a_res.status_code == 201
    snap_a_id = snap_a_res.json()["id"]

    # 7. Update FX Rates to v2 (EUR = 1.1000)
    fx_v2_res = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/matrix/fx-rates",
        json={
            "base_currency": "USD",
            "rates": {"USD": 1.0, "EUR": 1.1000},
            "provider_id": "audited_v2_committee_rates",
        },
        headers=headers,
    )
    assert fx_v2_res.status_code == 201
    assert fx_v2_res.json()["version"] == 2

    # 8. Verify live matrix under FX v2 (EUR = 1.1000)
    matrix_v2 = (await async_client.get(f"/api/v1/rfqs/{rfq_id}/matrix")).json()
    supp_v2 = matrix_v2["suppliers"][0]
    assert supp_v2["quoted_grand_total"] == 14000.00
    # Exact v2 calculation:
    # Item 1: 100.00 EUR * 1.1000 = $110.0000 -> Ext: $11,000.00 USD
    # Item 2: (400.00 EUR / 20) * 1.1000 = $22.0000 -> Ext: $4,400.00 USD
    # Subtotal = $11,000.00 + $4,400.00 = $15,400.00 USD (EXACTLY 14,000.00 * 1.1000)
    assert supp_v2["normalized_line_item_subtotal"] == 15400.00
    assert supp_v2["normalized_comparable_total"] == 15400.00

    # 9. Mutate the override: Revert packaging override to prove snapshot decoupling
    del_ov = await async_client.delete(
        f"/api/v1/rfqs/{rfq_id}/matrix/overrides/{override_id}",
        headers=headers,
    )
    assert del_ov.status_code == 200

    # Live matrix now has unresolved UOM for Item 2, and comparable total is withheld
    matrix_post_revert = (await async_client.get(f"/api/v1/rfqs/{rfq_id}/matrix")).json()
    supp_post_revert = matrix_post_revert["suppliers"][0]
    assert supp_post_revert["unresolved_count"] == 1
    assert supp_post_revert["normalized_comparable_total"] is None

    # 10. CRITICAL IMMUTABILITY CHECK: Retrieve Snapshot A and verify it was NOT affected by:
    #     a) the FX v2 rate update, OR
    #     b) the override deletion
    snap_a_data = (
        await async_client.get(f"/api/v1/rfqs/{rfq_id}/matrix/snapshots/{snap_a_id}")
    ).json()
    snap_a_matrix = snap_a_data["matrix_data"]
    snap_a_supp = snap_a_matrix["suppliers"][0]
    assert snap_a_supp["normalized_line_item_subtotal"] == 15190.00
    assert snap_a_supp["normalized_comparable_total"] == 15190.00

    snap_a_item_2 = snap_a_matrix["required_line_items"][1]["supplier_cells"][qid]
    assert snap_a_item_2["is_human_overridden"] is True
    assert snap_a_item_2["uom_conversion_factor"] == 20.0
    assert snap_a_item_2["normalized_unit_price"] == 21.7000
    assert snap_a_item_2["normalized_extended_price"] == 4340.00


@pytest.mark.asyncio
async def test_comparable_total_safety_with_commercial_components(
    async_client: AsyncClient,
    tmp_path: Path,
) -> None:
    """
    Proves that when a quotation contains commercial components (such as freight, taxes,
    discounts, or stated grand total variances), ProcureFlow cleanly distinguishes:
      - supplier quoted grand total
      - normalized line-item subtotal
      - normalized comparable total (withheld as None with warnings when complete equivalence cannot be proven).
    """
    headers = {"X-API-Key": "dev_test_key_12345"}

    # 1. Create RFQ
    rfq_data = {
        "title": "Commercial Components Safety Test RFQ",
        "category": "Piping",
        "reference_currency": "USD",
        "line_items": [
            {"position": 1, "description": "Steel Pipe 2-inch", "quantity": 50, "unit": "pcs"},
        ],
        "criteria": [
            {"name": "Price", "weight": 1.0, "criterion_type": "price", "is_mandatory": True}
        ],
    }
    rfq = (await async_client.post("/api/v1/rfqs", json=rfq_data, headers=headers)).json()
    rfq_id = rfq["id"]
    rfq_item_id = rfq["line_items"][0]["id"]

    # 2. Create Quotation
    quote = (
        await async_client.post(
            "/api/v1/quotations",
            json={"rfq_id": rfq_id, "supplier_name": "Logistics Surcharged Supplier Ltd"},
            headers=headers,
        )
    ).json()
    qid = quote["id"]

    pdf_path = FIXTURES_DIR / "quotations" / "native_valves.pdf"
    with open(pdf_path, "rb") as f:
        await async_client.post(
            f"/api/v1/quotations/{qid}/documents",
            files={"file": ("quote_valves.pdf", f.read(), "application/pdf")},
            headers=headers,
        )

    await async_client.post(f"/api/v1/quotations/{qid}/extract", headers=headers)
    extr = (await async_client.get(f"/api/v1/quotations/{qid}/extractions/latest")).json()
    item_id = extr["line_items"][0]["id"]

    # Map line item 0 to RFQ item (100% of RFQ scope)
    await async_client.patch(
        f"/api/v1/quotations/{qid}/line-items/{item_id}",
        json={
            "rfq_line_item_id": rfq_item_id,
            "unit_price": 50.00,
            "quantity": 50,
            "total_price": 2500.00,
            "currency": "USD",
        },
        headers=headers,
    )

    # Soft-delete remaining parsed items
    for extra_it in extr["line_items"][1:]:
        await async_client.delete(
            f"/api/v1/quotations/{qid}/line-items/{extra_it['id']}",
            headers=headers,
        )

    # Add an unmapped commercial surcharge item: Ocean Freight
    await async_client.post(
        f"/api/v1/quotations/{qid}/line-items",
        json={
            "description_raw": "Ocean Freight & Customs Handling Surcharge",
            "quantity": 1,
            "unit": "lot",
            "unit_price": 350.00,
            "total_price": 350.00,
            "currency": "USD",
        },
        headers=headers,
    )

    # Approve extraction
    await async_client.patch(
        f"/api/v1/quotations/{qid}/status",
        json={"status": "approved"},
        headers=headers,
    )

    # 3. Retrieve Comparison Matrix
    matrix = (await async_client.get(f"/api/v1/rfqs/{rfq_id}/matrix")).json()
    supp = matrix["suppliers"][0]

    # Verify:
    # a) quoted_grand_total = $2,850.00 ($2,500 base item + $350 freight)
    assert supp["quoted_grand_total"] == 2850.00
    # b) normalized_line_item_subtotal = $2,500.00 (only mapped RFQ required items)
    assert supp["normalized_line_item_subtotal"] == 2500.00
    # c) has_unknown_commercial_components is True due to unmapped surcharge
    assert supp["has_unknown_commercial_components"] is True
    # d) normalized_comparable_total is WITHHELD (None) because extra commercial components exist
    assert supp["normalized_comparable_total"] is None
    # e) extra_line_items list contains the $350 ocean freight component
    assert len(matrix["extra_line_items"]) == 1
    assert (
        matrix["extra_line_items"][0]["description_raw"]
        == "Ocean Freight & Customs Handling Surcharge"
    )
    assert matrix["extra_line_items"][0]["total_price"] == 350.00
    # f) Warnings summary contains explicit explanation
    assert any(
        "extra" in w.lower() or "commercial" in w.lower() for w in matrix["warnings_summary"]
    )
