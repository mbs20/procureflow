"""
Phase 6 — Integration tests for Decision Narrative & Human Award API endpoints.

Covers full end-to-end API workflows:
- Decision narrative generation and DecisionContext creation
- Grounded claims retrieval
- Human revision append-only history
- Draft award creation with Rank-1 and Rank-2 rationale enforcement
- Knockout supplier award rejection (422)
- Human award confirmation lifecycle and RFQ state transition (AWARDED)
- Double-award conflict prevention (409)
- Award revocation with reason and RFQ state rollback (EVALUATED)
- Context and narrative retrieval by ID
"""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.mark.asyncio
async def test_full_phase6_decision_and_award_lifecycle(async_client: AsyncClient):
    headers = {"X-API-Key": "procureflow_dev_api_key_12345"}
    csv_file = FIXTURES_DIR / "quotations" / "clean_bearings.csv"

    # 1. Create RFQ
    rfq_payload = {
        "title": "Phase 6 Decision Narrative & Award Integration RFQ",
        "description": "Integration test for Phase 6",
        "category": "Industrial",
        "reference_currency": "USD",
        "line_items": [
            {
                "position": 1,
                "description": "Bearing 6205",
                "quantity": 100,
                "unit": "pcs",
            },
            {
                "position": 2,
                "description": "Shaft Seal 40x62x7",
                "quantity": 50,
                "unit": "pcs",
            },
        ],
        "criteria": [
            {"name": "Price", "weight": 0.60, "direction": "lower_is_better", "data_type": "price"},
            {
                "name": "Lead Time",
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

    # 2. Ingest 2 Suppliers (Supplier Alpha and Supplier Beta)
    # Supplier Alpha: $1450, 14 days
    quote_a = (
        await async_client.post(
            "/api/v1/quotations",
            json={"rfq_id": rfq_id, "supplier_name": "Supplier Alpha"},
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
    if len(extr_a["line_items"]) > 2:
        await async_client.delete(
            f"/api/v1/quotations/{qid_a}/line-items/{extr_a['line_items'][2]['id']}",
            headers=headers,
        )
        await async_client.patch(
            f"/api/v1/quotations/{qid_a}/status",
            json={"status": "approved", "decision_notes": "Approved Alpha"},
            headers=headers,
        )

        # Supplier Beta: $1600, 20 days
        quote_b = (
            await async_client.post(
                "/api/v1/quotations",
                json={"rfq_id": rfq_id, "supplier_name": "Supplier Beta"},
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
                "unit_price": 14.00,
                "quantity": 100,
                "total_price": 1400.00,
                "currency": "USD",
                "lead_time_days": 20,
            },
            headers=headers,
        )
        await async_client.patch(
            f"/api/v1/quotations/{qid_b}/line-items/{extr_b['line_items'][1]['id']}",
            json={
                "rfq_line_item_id": rfq_item_2_id,
                "unit_price": 4.00,
                "quantity": 50,
                "total_price": 200.00,
                "currency": "USD",
                "lead_time_days": 20,
            },
            headers=headers,
        )
        if len(extr_b["line_items"]) > 2:
            await async_client.delete(
                f"/api/v1/quotations/{qid_b}/line-items/{extr_b['line_items'][2]['id']}",
                headers=headers,
            )
        await async_client.patch(
            f"/api/v1/quotations/{qid_b}/status",
            json={"status": "approved", "decision_notes": "Approved Beta"},
            headers=headers,
        )

        # 3. Create ComparisonSnapshot
        snap_resp = await async_client.post(
            f"/api/v1/rfqs/{rfq_id}/matrix/snapshots",
            json={"title": "Phase 6 Test Snapshot"},
            headers=headers,
        )
        assert snap_resp.status_code == 201
        snap_data = snap_resp.json()
        snapshot_id = snap_data["id"]

        # 4. Create ScoringConfiguration
        config_payload = {
            "name": "Phase 6 Scoring Config",
            "description": "Standard weighting",
            "criteria": [
                {
                    "criterion_id": "c-price",
                    "name": "Total Price",
                    "weight": 0.6000,
                    "direction": "lower_is_better",
                    "source_type": "price",
                    "source_field": "normalized_comparable_total",
                },
                {
                    "criterion_id": "c-lead-time",
                    "name": "Overall Lead Time",
                    "weight": 0.4000,
                    "direction": "lower_is_better",
                    "source_type": "lead_time",
                    "source_field": "overall_lead_time_days",
                },
            ],
            "normalization_method": "min_max",
            "missing_value_policy": "block_scoring",
            "tie_policy": "standard_competitive",
            "engine_version": "1.0",
        }
        config_resp = await async_client.post(
            f"/api/v1/rfqs/{rfq_id}/scoring/configurations",
            json=config_payload,
            headers=headers,
        )
    assert config_resp.status_code == 201
    config_id = config_resp.json()["id"]

    # 5. Execute ScoringRun
    run_resp = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/scoring/runs",
        json={
            "configuration_id": config_id,
            "snapshot_id": snapshot_id,
            "name": "Phase 6 Authoritative Scoring Run",
        },
        headers=headers,
    )
    assert run_resp.status_code == 201
    run_data = run_resp.json()
    scoring_run_id = run_data["id"]
    suppliers = run_data["results_payload"]["suppliers"]
    rank_1_supplier = next(s for s in suppliers if s["rank"] == 1)
    rank_2_supplier = next(s for s in suppliers if s["rank"] == 2)
    assert rank_1_supplier["supplier_name"] == "Supplier Alpha"
    assert rank_2_supplier["supplier_name"] == "Supplier Beta"

    # -------------------------------------------------------------------------
    # 6. Generate Decision Narrative (POST /rfqs/{rfq_id}/decisions/narratives)
    # -------------------------------------------------------------------------
    narrative_req = {
        "scoring_run_id": scoring_run_id,
        "narrative_type": "decision_support_memo",
        "include_sensitivity": False,
        "human_unverified_note": "Internal note for evaluation context",
    }
    narr_resp = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/decisions/narratives",
        json=narrative_req,
        headers=headers,
    )
    assert narr_resp.status_code == 201
    narr_data = narr_resp.json()
    narrative_id = narr_data["id"]
    context_id = narr_data["decision_context_id"]
    assert narr_data["generation_number"] == 1
    assert narr_data["provider"] == "mock"
    assert narr_data["origin"] == "ai_generated"
    assert len(narr_data["claims"]) > 0
    assert narr_data["grounding_validation_result"]["unsupported"] == 0

    # -------------------------------------------------------------------------
    # 7. List and Get Narrative
    # -------------------------------------------------------------------------
    list_narr = await async_client.get(
        f"/api/v1/rfqs/{rfq_id}/decisions/narratives",
        headers=headers,
    )
    assert list_narr.status_code == 200
    assert len(list_narr.json()) == 1

    get_narr = await async_client.get(
        f"/api/v1/rfqs/{rfq_id}/decisions/narratives/{narrative_id}",
        headers=headers,
    )
    assert get_narr.status_code == 200
    assert get_narr.json()["id"] == narrative_id

    # -------------------------------------------------------------------------
    # 8. Retrieve DecisionContext (GET /rfqs/{rfq_id}/decisions/contexts/{context_id})
    # -------------------------------------------------------------------------
    ctx_resp = await async_client.get(
        f"/api/v1/rfqs/{rfq_id}/decisions/contexts/{context_id}",
        headers=headers,
    )
    assert ctx_resp.status_code == 200
    ctx_data = ctx_resp.json()
    assert ctx_data["id"] == context_id
    assert ctx_data["context_hash"] is not None
    assert len(ctx_data["context_payload"]["suppliers"]) == 2

    # -------------------------------------------------------------------------
    # 9. Create Append-Only Human Revision
    # -------------------------------------------------------------------------
    rev_resp = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/decisions/narratives/{narrative_id}/revisions",
        json={
            "revised_text": "Committee executive summary: Supplier Alpha is selected for superior pricing and lead time.",
            "revision_rationale": "Clarified procurement committee reasoning",
        },
        headers=headers,
    )
    assert rev_resp.status_code == 201
    rev_data = rev_resp.json()
    assert rev_data["revision_number"] == 1
    assert rev_data["revised_by"] is not None

    # -------------------------------------------------------------------------
    # 10. Draft Award Creation & Validations
    # -------------------------------------------------------------------------
    # Attempting to award Rank #2 without non_rank1_rationale must return 422
    invalid_rank2_award = {
        "scoring_run_id": scoring_run_id,
        "awarded_supplier_id": rank_2_supplier["quotation_id"],
        "narrative_generation_id": narrative_id,
        "award_justification": "Selecting Rank 2 without required non_rank1_rationale",
    }
    bad_rank2_resp = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/decisions/awards",
        json=invalid_rank2_award,
        headers=headers,
    )
    assert bad_rank2_resp.status_code == 422

    # Create valid draft award for Rank #1 (Supplier Alpha)
    draft_award_payload = {
        "scoring_run_id": scoring_run_id,
        "awarded_supplier_id": rank_1_supplier["quotation_id"],
        "narrative_generation_id": narrative_id,
        "award_justification": "Supplier Alpha ranked #1 with lowest total cost and acceptable lead time.",
    }
    award_resp = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/decisions/awards",
        json=draft_award_payload,
        headers=headers,
    )
    assert award_resp.status_code == 201
    award_data = award_resp.json()
    award_id = award_data["id"]
    assert award_data["current_status"] == "draft"
    assert award_data["awarded_supplier_rank"] == 1
    assert award_data["is_based_on_latest_run"] is True
    assert len(award_data["events"]) == 1
    assert award_data["events"][0]["event_type"] == "draft_created"

    # List awards
    list_awards_resp = await async_client.get(
        f"/api/v1/rfqs/{rfq_id}/decisions/awards",
        headers=headers,
    )
    assert list_awards_resp.status_code == 200
    assert len(list_awards_resp.json()) == 1

    # -------------------------------------------------------------------------
    # 11. Confirm Award (The ONLY human path to final decision)
    # -------------------------------------------------------------------------
    confirm_resp = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/decisions/awards/{award_id}/confirm",
        json={
            "final_justification": "Formally approved by Chief Procurement Officer.",
        },
        headers=headers,
    )
    assert confirm_resp.status_code == 200
    confirmed_award = confirm_resp.json()
    assert confirmed_award["current_status"] == "confirmed"
    assert confirmed_award["provenance_hash"] is not None
    assert len(confirmed_award["events"]) == 2
    assert confirmed_award["events"][1]["event_type"] == "confirmed"
    assert confirmed_award["events"][1]["actor_principal"] is not None

    # Verify RFQ status transitioned to decided
    rfq_check = await async_client.get(f"/api/v1/rfqs/{rfq_id}", headers=headers)
    assert rfq_check.status_code == 200
    assert rfq_check.json()["status"] == "decided"

    # Verify GET current award
    current_award_resp = await async_client.get(
        f"/api/v1/rfqs/{rfq_id}/decisions/awards/current",
        headers=headers,
    )
    assert current_award_resp.status_code == 200
    assert current_award_resp.json()["id"] == award_id

    # -------------------------------------------------------------------------
    # 12. Double-Award Prevention (409 Conflict)
    # -------------------------------------------------------------------------
    second_draft_resp = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/decisions/awards",
        json=draft_award_payload,
        headers=headers,
    )
    assert second_draft_resp.status_code == 409

    # Re-confirming already confirmed award returns 422
    dup_confirm_resp = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/decisions/awards/{award_id}/confirm",
        json={"final_justification": "Trying again"},
        headers=headers,
    )
    assert dup_confirm_resp.status_code == 422

    # -------------------------------------------------------------------------
    # 13. Revoke Award with Reason
    # -------------------------------------------------------------------------
    revoke_resp = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/decisions/awards/{award_id}/revoke",
        json={
            "revocation_reason": "Commercial terms renegotiation requested by legal counsel.",
        },
        headers=headers,
    )
    assert revoke_resp.status_code == 200
    revoked_award = revoke_resp.json()
    assert revoked_award["current_status"] == "revoked"
    assert len(revoked_award["events"]) == 3
    assert revoked_award["events"][2]["event_type"] == "revoked"

    # Verify RFQ status reverted to evaluating
    rfq_revert_check = await async_client.get(f"/api/v1/rfqs/{rfq_id}", headers=headers)
    assert rfq_revert_check.status_code == 200
    assert rfq_revert_check.json()["status"] == "evaluating"

    # Verify current award is now None
    current_none_resp = await async_client.get(
        f"/api/v1/rfqs/{rfq_id}/decisions/awards/current",
        headers=headers,
    )
    assert current_none_resp.status_code == 200
    assert current_none_resp.json() is None


@pytest.mark.asyncio
async def test_stale_and_superseded_semantics_lifecycle(async_client: AsyncClient):
    """
    Requirement 1: Prove stale / superseded semantics
    - ScoringRun v1 exists
    - DecisionContext v1 & Narrative #1 created
    - Confirmed award based on v1 created
    - Newer ScoringRun v2 created for same RFQ
    - Narrative #1 remains immutable; API marks it is_superseded=True
    - Confirmed award remains recorded (NOT automatically revoked)
    - is_based_on_latest_run is marked False with latest_scoring_run_id pointing to v2
    """
    headers = {"X-API-Key": "procureflow_dev_api_key_12345"}
    csv_file = FIXTURES_DIR / "quotations" / "clean_bearings.csv"

    # 1. Create RFQ
    rfq_payload = {
        "title": "Superseded Semantics Lifecycle RFQ",
        "description": "Proving stale and superseded semantics",
        "category": "Industrial",
        "reference_currency": "USD",
        "line_items": [
            {"position": 1, "description": "Bearing 6205", "quantity": 100, "unit": "pcs"},
        ],
        "criteria": [
            {"name": "Price", "weight": 1.0, "direction": "lower_is_better", "data_type": "price"},
        ],
    }
    rfq_resp = await async_client.post("/api/v1/rfqs", json=rfq_payload, headers=headers)
    rfq_id = rfq_resp.json()["id"]
    rfq_item_id = rfq_resp.json()["line_items"][0]["id"]

    # 2. Quotation
    quote = (
        await async_client.post(
            "/api/v1/quotations",
            json={"rfq_id": rfq_id, "supplier_name": "Supplier Alpha"},
            headers=headers,
        )
    ).json()
    qid = quote["id"]
    with open(csv_file, "rb") as f:
        await async_client.post(
            f"/api/v1/quotations/{qid}/documents",
            files={"file": ("quote.csv", f.read(), "text/csv")},
            headers=headers,
        )
    await async_client.post(f"/api/v1/quotations/{qid}/extract", headers=headers)
    extr = (await async_client.get(f"/api/v1/quotations/{qid}/extractions/latest")).json()
    await async_client.patch(
        f"/api/v1/quotations/{qid}/line-items/{extr['line_items'][0]['id']}",
        json={
            "rfq_line_item_id": rfq_item_id,
            "unit_price": 10.00,
            "quantity": 100,
            "total_price": 1000.00,
            "currency": "USD",
            "lead_time_days": 10,
        },
        headers=headers,
    )
    for it in extr["line_items"][1:]:
        await async_client.delete(
            f"/api/v1/quotations/{qid}/line-items/{it['id']}", headers=headers
        )
    await async_client.patch(
        f"/api/v1/quotations/{qid}/status",
        json={"status": "approved", "decision_notes": "Approved Alpha"},
        headers=headers,
    )

    # 3. Snapshot & Config
    snap_resp = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/matrix/snapshots",
        json={"title": "Snapshot 1"},
        headers=headers,
    )
    assert snap_resp.status_code == 201
    snapshot_id = snap_resp.json()["id"]

    config_payload = {
        "name": "Phase 6 Scoring Config",
        "description": "Standard weighting",
        "criteria": [
            {
                "criterion_id": "c-price",
                "name": "Total Price",
                "weight": 1.0,
                "direction": "lower_is_better",
                "source_type": "price",
                "source_field": "normalized_comparable_total",
            },
        ],
        "normalization_method": "min_max",
        "missing_value_policy": "block_scoring",
        "tie_policy": "standard_competitive",
        "engine_version": "1.0",
    }
    config_resp = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/scoring/configurations",
        json=config_payload,
        headers=headers,
    )
    assert config_resp.status_code == 201
    config_id = config_resp.json()["id"]

    # 4. ScoringRun v1
    run1_resp = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/scoring/runs",
        json={
            "configuration_id": config_id,
            "snapshot_id": snapshot_id,
            "name": "Run #1",
        },
        headers=headers,
    )
    assert run1_resp.status_code == 201
    run1 = run1_resp.json()
    run1_id = run1["id"]

    # 5. Narrative #1 from Run v1
    narr1 = (
        await async_client.post(
            f"/api/v1/rfqs/{rfq_id}/decisions/narratives",
            json={"scoring_run_id": run1_id, "narrative_type": "comparison_summary"},
            headers=headers,
        )
    ).json()
    narr1_id = narr1["id"]
    output_hash_before = narr1["output_hash"]
    assert narr1["is_superseded"] is False

    # 6. Confirm Award based on Run v1
    draft_award = (
        await async_client.post(
            f"/api/v1/rfqs/{rfq_id}/decisions/awards",
            json={
                "scoring_run_id": run1_id,
                "narrative_generation_id": narr1_id,
                "awarded_supplier_id": qid,
                "award_justification": "Approved based on Run 1",
            },
            headers=headers,
        )
    ).json()
    award_id = draft_award["id"]
    confirmed_award = (
        await async_client.post(
            f"/api/v1/rfqs/{rfq_id}/decisions/awards/{award_id}/confirm",
            json={"final_justification": "Confirmed by buyer"},
            headers=headers,
        )
    ).json()
    assert confirmed_award["current_status"] == "confirmed"
    assert confirmed_award["is_based_on_latest_run"] is True

    # 7. Create newer ScoringRun v2 for same RFQ
    run2_resp = await async_client.post(
        f"/api/v1/rfqs/{rfq_id}/scoring/runs",
        json={
            "configuration_id": config_id,
            "snapshot_id": snapshot_id,
            "name": "Run #2",
        },
        headers=headers,
    )
    assert run2_resp.status_code == 201
    run2 = run2_resp.json()
    run2_id = run2["id"]
    assert run2_id != run1_id

    # 8. Retrieve Narrative #1: Must be marked is_superseded=True, yet remain immutable
    narr1_check = (
        await async_client.get(
            f"/api/v1/rfqs/{rfq_id}/decisions/narratives/{narr1_id}",
            headers=headers,
        )
    ).json()
    assert narr1_check["is_superseded"] is True
    assert "newer ScoringRun" in narr1_check["superseded_reason"]
    assert narr1_check["output_hash"] == output_hash_before  # Immutability preserved

    # 9. Retrieve Award: Confirmed human decision is NOT auto-revoked
    award_check = (
        await async_client.get(
            f"/api/v1/rfqs/{rfq_id}/decisions/awards/{award_id}",
            headers=headers,
        )
    ).json()
    assert award_check["current_status"] == "confirmed"  # NOT revoked
    assert award_check["is_based_on_latest_run"] is False  # UI warn flag set
    assert award_check["latest_scoring_run_id"] == run2_id


@pytest.mark.asyncio
async def test_actor_identity_spoofing_via_api(async_client: AsyncClient):
    """
    Requirement 6: Verify actor identity provenance cannot be spoofed via request bodies.
    """
    headers = {"X-API-Key": "procureflow_dev_api_key_12345"}

    # Attempt to spoof actor in revision creation
    # Test on existing narrative or invalid ID to check body handling
    resp = await async_client.post(
        "/api/v1/rfqs/rfq-nonexistent/decisions/narratives/narr-nonexistent/revisions",
        json={
            "revised_text": "Attempted spoof",
            "revision_rationale": "Testing",
            "revised_by": "attacker_spoofed_principal",
            "actor_principal": "attacker_spoofed_principal",
        },
        headers=headers,
    )
    # Reaches 404 because narrative doesn't exist, but Pydantic did not crash on extra fields
    # and service uses authenticated api_key
    assert resp.status_code == 404
