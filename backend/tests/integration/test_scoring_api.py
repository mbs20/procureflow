from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.mark.asyncio
async def test_full_phase5_scoring_lifecycle_and_provenance(async_client: AsyncClient):
    """
    Complete Phase 5 Integration Test:
    1. Setup RFQ with 2 required line items.
    2. Ingest and approve 3 supplier quotations (A, B, C):
       - Supplier A: $1,450 USD total, 14 days lead time, Net 30 payment terms
       - Supplier B: $1,550 USD total, 21 days lead time, Net 60 payment terms
       - Supplier C: $1,200 USD total, 45 days lead time, 100% Advance (fails knockout!)
    3. Compile Phase 4 matrix and freeze an immutable ComparisonSnapshot.
    4. Create ScoringConfiguration v1:
       - Total Price (50%, lower is better)
       - Lead Time (30%, lower is better, knockout threshold = 30 days)
       - Payment Terms (20%, higher is better, explicit categorical map: Net 60=100, Net 30=70, Advance=20)
    5. Execute ScoringRun #1 against the ComparisonSnapshot:
       - Verify Supplier C is KNOCKOUT_FAILED due to 45 days > 30 days.
       - Verify Supplier C's $1,200 price does NOT distort min price (min price is $1,450 from A).
       - Verify Supplier A is Rank 1 and Supplier B is Rank 2.
       - Verify complete formula audit strings and provenance.
    6. In-memory simulation via POST /simulate (no database mutation).
    7. In-memory sensitivity analysis via POST /sensitivity:
       - Proportional weight redistribution maintaining sum = 100%.
       - Numerical bisection breakeven for Supplier B to achieve Rank 1.
    8. Create ScoringConfiguration v2 (altering weights and policy).
    9. Execute ScoringRun #2 against the snapshot.
    10. Verify historical ScoringRun #1 remains 100% immutable and independent.
    """
    headers = {"X-API-Key": "procureflow_dev_api_key_12345"}
    csv_file = FIXTURES_DIR / "quotations" / "clean_bearings.csv"

    # -------------------------------------------------------------------------
    # 1. Create RFQ
    # -------------------------------------------------------------------------
    rfq_payload = {
        "title": "Industrial High-Load Bearing Package - Phase 5 Scoring",
        "description": "Evaluation test RFQ",
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
            {"name": "Price", "weight": 0.50, "direction": "lower_is_better", "data_type": "price"},
            {
                "name": "Lead Time",
                "weight": 0.30,
                "direction": "lower_is_better",
                "data_type": "days",
            },
            {
                "name": "Payment Terms",
                "weight": 0.20,
                "direction": "higher_is_better",
                "data_type": "enum",
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
    # 2. Ingest 3 Suppliers
    # -------------------------------------------------------------------------
    # Supplier A: $1450, 14 days, Net 30
    quote_a = (
        await async_client.post(
            "/api/v1/quotations",
            json={"rfq_id": rfq_id, "supplier_name": "Supplier A"},
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
    await async_client.patch(
        f"/api/v1/quotations/{qid_a}/line-items/{extr_a['line_items'][0]['id']}",
        json={
            "rfq_line_item_id": rfq_item_1_id,
            "unit_price": 12.50,
            "quantity": 100,
            "total_price": 1250.00,
            "currency": "USD",
            "lead_time_days": 14,
        },
        headers=headers,
    )
    await async_client.patch(
        f"/api/v1/quotations/{qid_a}/line-items/{extr_a['line_items'][1]['id']}",
        json={
            "rfq_line_item_id": rfq_item_2_id,
            "unit_price": 4.00,
            "quantity": 50,
            "total_price": 200.00,
            "currency": "USD",
            "lead_time_days": 14,
        },
        headers=headers,
    )
    # Metadata fields
    for field in extr_a["fields"]:
        if field["field_name"] == "payment_terms":
            await async_client.patch(
                f"/api/v1/quotations/{qid_a}/fields/{field['id']}",
                json={"field_value": "Net 30"},
                headers=headers,
            )
        if field["field_name"] == "lead_time":
            await async_client.patch(
                f"/api/v1/quotations/{qid_a}/fields/{field['id']}",
                json={"field_value": "14 calendar days"},
                headers=headers,
            )
    if len(extr_a["line_items"]) > 2:
        await async_client.delete(
            f"/api/v1/quotations/{qid_a}/line-items/{extr_a['line_items'][2]['id']}",
            headers=headers,
        )
    await async_client.post(
        f"/api/v1/quotations/{qid_a}/review-decision",
        json={"status": "approved", "decision_notes": "Approved A"},
        headers=headers,
    )

    # Supplier B: $1550, 21 days, Net 60
    quote_b = (
        await async_client.post(
            "/api/v1/quotations",
            json={"rfq_id": rfq_id, "supplier_name": "Supplier B"},
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
    await async_client.patch(
        f"/api/v1/quotations/{qid_b}/line-items/{extr_b['line_items'][0]['id']}",
        json={
            "rfq_line_item_id": rfq_item_1_id,
            "unit_price": 13.00,
            "quantity": 100,
            "total_price": 1300.00,
            "currency": "USD",
            "lead_time_days": 21,
        },
        headers=headers,
    )
    await async_client.patch(
        f"/api/v1/quotations/{qid_b}/line-items/{extr_b['line_items'][1]['id']}",
        json={
            "rfq_line_item_id": rfq_item_2_id,
            "unit_price": 5.00,
            "quantity": 50,
            "total_price": 250.00,
            "currency": "USD",
            "lead_time_days": 21,
        },
        headers=headers,
    )
    if len(extr_b["line_items"]) > 2:
        await async_client.delete(
            f"/api/v1/quotations/{qid_b}/line-items/{extr_b['line_items'][2]['id']}",
            headers=headers,
        )
    await async_client.post(
        f"/api/v1/quotations/{qid_b}/review-decision",
        json={"status": "approved", "decision_notes": "Approved B"},
        headers=headers,
    )

    # Supplier C: $1200, 45 days (Knockout!), Advance
    quote_c = (
        await async_client.post(
            "/api/v1/quotations",
            json={"rfq_id": rfq_id, "supplier_name": "Supplier C"},
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
    await async_client.patch(
        f"/api/v1/quotations/{qid_c}/line-items/{extr_c['line_items'][0]['id']}",
        json={
            "rfq_line_item_id": rfq_item_1_id,
            "unit_price": 10.00,
            "quantity": 100,
            "total_price": 1000.00,
            "currency": "USD",
            "lead_time_days": 45,
        },
        headers=headers,
    )
    await async_client.patch(
        f"/api/v1/quotations/{qid_c}/line-items/{extr_c['line_items'][1]['id']}",
        json={
            "rfq_line_item_id": rfq_item_2_id,
            "unit_price": 4.00,
            "quantity": 50,
            "total_price": 200.00,
            "currency": "USD",
            "lead_time_days": 45,
        },
        headers=headers,
    )
    if len(extr_c["line_items"]) > 2:
        await async_client.delete(
            f"/api/v1/quotations/{qid_c}/line-items/{extr_c['line_items'][2]['id']}",
            headers=headers,
        )
    await async_client.post(
        f"/api/v1/quotations/{qid_c}/review-decision",
        json={"status": "approved", "decision_notes": "Approved C"},
        headers=headers,
    )

    # -------------------------------------------------------------------------
    # 2.5 Apply Payment Terms Overrides (Phase 4 Human Review)
    # -------------------------------------------------------------------------
    await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/matrix/overrides",
        json={
            "quotation_id": qid_a,
            "field_name": "payment_terms",
            "override_value": {"payment_terms": "Net 30", "term_code": "NET_30"},
            "override_reason": "Verified Net 30 from commercial agreement",
        },
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/matrix/overrides",
        json={
            "quotation_id": qid_b,
            "field_name": "payment_terms",
            "override_value": {"payment_terms": "Net 60", "term_code": "NET_60"},
            "override_reason": "Verified Net 60 from commercial agreement",
        },
        headers=headers,
    )

    # -------------------------------------------------------------------------
    # 3. Create ComparisonSnapshot
    # -------------------------------------------------------------------------
    snap_resp = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/matrix/snapshots",
        json={"title": "Official Baseline Snapshot for Phase 5 Scoring"},
        headers=headers,
    )
    assert snap_resp.status_code == 201
    snapshot_id = snap_resp.json()["id"]

    # -------------------------------------------------------------------------
    # 4. Create ScoringConfiguration v1
    # -------------------------------------------------------------------------
    config_v1_payload = {
        "name": "Production Evaluation Model v1",
        "description": "Deterministic weighted scoring with knockout rule",
        "criteria": [
            {
                "criterion_id": "c-price",
                "name": "Total Price",
                "weight": 0.5000,
                "direction": "lower_is_better",
                "source_type": "price",
                "source_field": "normalized_comparable_total",
            },
            {
                "criterion_id": "c-lead-time",
                "name": "Overall Lead Time",
                "weight": 0.3000,
                "direction": "lower_is_better",
                "source_type": "lead_time",
                "source_field": "overall_lead_time_days",
                "is_knockout": True,
                "knockout_threshold": 30.0,
            },
            {
                "criterion_id": "c-payment-terms",
                "name": "Payment Terms Utility",
                "weight": 0.2000,
                "direction": "higher_is_better",
                "source_type": "payment_terms",
                "source_field": "payment_terms_code",
                "categorical_map": {
                    "NET_60": 100.0,
                    "NET_30": 70.0,
                    "ADVANCE": 20.0,
                    "CUSTOM": 50.0,
                },
            },
        ],
        "normalization_method": "min_max",
        "missing_value_policy": "block_scoring",
        "tie_policy": "standard_competitive",
        "engine_version": "1.0",
    }
    cfg_resp = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/scoring/configurations",
        json=config_v1_payload,
        headers=headers,
    )
    assert cfg_resp.status_code == 201
    cfg_v1 = cfg_resp.json()
    config_v1_id = cfg_v1["id"]
    assert cfg_v1["version"] == 1
    assert cfg_v1["is_active"] is True

    # -------------------------------------------------------------------------
    # 5. Execute ScoringRun #1 against ComparisonSnapshot
    # -------------------------------------------------------------------------
    run_resp = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/scoring/runs",
        json={
            "snapshot_id": snapshot_id,
            "configuration_id": config_v1_id,
            "name": "Official Evaluation Run #1",
            "notes": "First round evaluation",
        },
        headers=headers,
    )
    assert run_resp.status_code == 201
    run_1 = run_resp.json()
    run_1_id = run_1["id"]
    results_1 = run_1["results_payload"]

    assert results_1["eligible_suppliers_count"] == 2
    assert results_1["knockout_suppliers_count"] == 1

    suppliers_1 = results_1["suppliers"]
    supp_c_res = next(s for s in suppliers_1 if s["quotation_id"] == qid_c)
    assert supp_c_res["eligibility_status"] == "knockout_failed"
    assert supp_c_res["rank"] is None
    assert any("exceeds maximum knockout threshold 30" in r for r in supp_c_res["knockout_reasons"])

    supp_a_res = next(s for s in suppliers_1 if s["quotation_id"] == qid_a)
    supp_b_res = next(s for s in suppliers_1 if s["quotation_id"] == qid_b)

    assert supp_a_res["eligibility_status"] == "eligible"
    assert supp_b_res["eligibility_status"] == "eligible"

    # Supplier A price: 1450 (min) vs 1550 (max). Lower is better. A gets 100 on price, B gets 0.
    # Supplier A lead time: 14 days (min) vs 21 days (max). A gets 100, B gets 0.
    # Supplier B payment terms: Net 60 (100) vs Net 30 (70). B gets 100 on payment terms, A gets 0.
    # A total: 50 + 30 + 0 = 80.00
    # B total: 0 + 0 + 20 = 20.00
    assert float(supp_a_res["total_score"]) == 80.0
    assert supp_a_res["rank"] == 1

    assert float(supp_b_res["total_score"]) == 20.0
    assert supp_b_res["rank"] == 2

    # Check complete formula provenance
    a_price_crit = next(
        b for b in supp_a_res["criteria_breakdown"] if b["criterion_id"] == "c-price"
    )
    assert "formula_audit" in a_price_crit
    assert "source_path" in a_price_crit
    assert a_price_crit["source_path"] == f"suppliers[{qid_a}].normalized_comparable_total"

    # -------------------------------------------------------------------------
    # 6. In-Memory Simulation
    # -------------------------------------------------------------------------
    sim_resp = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/scoring/simulate",
        json={"snapshot_id": snapshot_id, "configuration_id": config_v1_id},
        headers=headers,
    )
    assert sim_resp.status_code == 200
    sim_scores = sim_resp.json()
    assert len(sim_scores) == 3

    # -------------------------------------------------------------------------
    # 7. In-Memory Sensitivity Analysis & Bisection Breakeven
    # -------------------------------------------------------------------------
    sens_resp = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/scoring/sensitivity",
        json={
            "snapshot_id": snapshot_id,
            "configuration_id": config_v1_id,
            "swept_criterion_id": "c-price",
            "locked_criterion_ids": ["c-payment-terms"],
            "step_size": 0.10,
            "include_breakeven": True,
            "breakeven_candidate_id": qid_b,
        },
        headers=headers,
    )
    assert sens_resp.status_code == 200
    sens_data = sens_resp.json()
    assert sens_data["swept_criterion_id"] == "c-price"
    assert "weight_redistribution_rule" in sens_data
    assert len(sens_data["points"]) > 0

    # Verify redistributed weights sum exactly to 1.0000 at each point
    for pt in sens_data["points"]:
        total_w = sum(float(v) for v in pt["redistributed_weights"].values())
        assert abs(total_w - 1.0) < 0.001

    # Verify breakeven calculation
    breakeven = sens_data["breakeven"]
    assert breakeven is not None
    assert breakeven["candidate_id"] == qid_b
    assert breakeven["feasible"] is True
    assert float(breakeven["required_price"]) <= 1450.0  # Must match/undercut A to take price lead
    assert float(breakeven["required_price"]) >= 1440.0
    assert breakeven["convergence_steps"] > 0

    # -------------------------------------------------------------------------
    # 8. Create ScoringConfiguration v2
    # -------------------------------------------------------------------------
    config_v2_payload = {
        "name": "Production Evaluation Model v2 (Payment Terms Prioritized)",
        "description": "Shifted weights toward cash flow and terms",
        "criteria": [
            {
                "criterion_id": "c-price",
                "name": "Total Price",
                "weight": 0.3000,
                "direction": "lower_is_better",
                "source_type": "price",
                "source_field": "normalized_comparable_total",
            },
            {
                "criterion_id": "c-lead-time",
                "name": "Overall Lead Time",
                "weight": 0.1000,
                "direction": "lower_is_better",
                "source_type": "lead_time",
                "source_field": "overall_lead_time_days",
                "is_knockout": True,
                "knockout_threshold": 30.0,
            },
            {
                "criterion_id": "c-payment-terms",
                "name": "Payment Terms Utility",
                "weight": 0.6000,  # Heavily favored!
                "direction": "higher_is_better",
                "source_type": "payment_terms",
                "source_field": "payment_terms_code",
                "categorical_map": {
                    "NET_60": 100.0,
                    "NET_30": 70.0,
                    "ADVANCE": 20.0,
                    "CUSTOM": 50.0,
                },
            },
        ],
        "normalization_method": "min_max",
        "missing_value_policy": "block_scoring",
        "tie_policy": "standard_competitive",
        "engine_version": "1.0",
    }
    cfg2_resp = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/scoring/configurations",
        json=config_v2_payload,
        headers=headers,
    )
    assert cfg2_resp.status_code == 201
    cfg_v2 = cfg2_resp.json()
    config_v2_id = cfg_v2["id"]
    assert cfg_v2["version"] == 2

    # -------------------------------------------------------------------------
    # 9. Execute ScoringRun #2
    # -------------------------------------------------------------------------
    run_2_resp = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/scoring/runs",
        json={
            "snapshot_id": snapshot_id,
            "configuration_id": config_v2_id,
            "name": "Evaluation Run #2 (Terms Prioritized)",
        },
        headers=headers,
    )
    assert run_2_resp.status_code == 201
    run_2 = run_2_resp.json()
    results_2 = run_2["results_payload"]
    supp_b_v2 = next(s for s in results_2["suppliers"] if s["quotation_id"] == qid_b)
    supp_a_v2 = next(s for s in results_2["suppliers"] if s["quotation_id"] == qid_a)

    # In v2, B gets 60 points from Payment terms (0.60 * 100) and 0 on price/lead time -> total 60.0
    # A gets 30 points on price + 10 on lead time + 0 on terms -> total 40.0
    # Under v2, Supplier B takes Rank 1!
    assert float(supp_b_v2["total_score"]) == 60.0
    assert supp_b_v2["rank"] == 1
    assert float(supp_a_v2["total_score"]) == 40.0
    assert supp_a_v2["rank"] == 2

    # -------------------------------------------------------------------------
    # 10. Verify Historical Run #1 Immutability
    # -------------------------------------------------------------------------
    fetch_run_1 = (await async_client.get(f"/api/v1/rfqs/{rfq_id}/scoring/runs/{run_1_id}")).json()
    assert fetch_run_1["configuration_id"] == config_v1_id
    res_1_reloaded = fetch_run_1["results_payload"]
    supp_a_reloaded = next(s for s in res_1_reloaded["suppliers"] if s["quotation_id"] == qid_a)
    supp_b_reloaded = next(s for s in res_1_reloaded["suppliers"] if s["quotation_id"] == qid_b)

    # Historical run #1 still ranks Supplier A as Rank 1 with score 80.00!
    assert float(supp_a_reloaded["total_score"]) == 80.0
    assert supp_a_reloaded["rank"] == 1
    assert float(supp_b_reloaded["total_score"]) == 20.0
    assert supp_b_reloaded["rank"] == 2
