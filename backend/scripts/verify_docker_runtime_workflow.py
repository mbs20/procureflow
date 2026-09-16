"""
Verification script for Phase 6 Docker runtime gate.
Executes against the running FastAPI backend in Docker container.
"""

import sys
import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"
HEADERS = {"X-API-Key": "procureflow_dev_api_key_12345"}

def wait_for_extraction(qid, max_retries=20):
    import time
    for _ in range(max_retries):
        resp = httpx.get(f"{BASE_URL}/quotations/{qid}/extractions/latest", headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json()
            if "line_items" in data:
                return data
        time.sleep(0.5)
    raise TimeoutError(f"Extraction timed out for quotation {qid}")

def run_gate():
    print("=== Step 0: Checking Backend Health ===")
    r = httpx.get(f"{BASE_URL}/health", headers=HEADERS)
    assert r.status_code == 200, f"Health check failed: {r.status_code} {r.text}"
    health_data = r.json()
    print("Health response:", health_data)
    assert health_data["status"] == "healthy"
    assert health_data["database"]["status"] == "healthy"
    assert health_data["redis"]["status"] == "healthy"

    print("\n=== Step 1: Creating RFQ ===")
    rfq_payload = {
        "title": "Docker Gate Phase 6 Decision RFQ",
        "description": "Docker runtime verification for Phase 6",
        "category": "Industrial",
        "reference_currency": "USD",
        "line_items": [
            {"position": 1, "description": "High Precision Valve 100mm", "quantity": 100, "unit": "pcs"},
            {"position": 2, "description": "Pressure Seal Kit", "quantity": 50, "unit": "pcs"},
        ],
        "criteria": [
            {"name": "Price", "weight": 0.60, "direction": "lower_is_better", "data_type": "price"},
            {"name": "Lead Time", "weight": 0.40, "direction": "lower_is_better", "data_type": "days"},
        ],
    }
    r = httpx.post(f"{BASE_URL}/rfqs", json=rfq_payload, headers=HEADERS)
    assert r.status_code == 201, f"Create RFQ failed: {r.status_code} {r.text}"
    rfq = r.json()
    rfq_id = rfq["id"]
    item_1_id = rfq["line_items"][0]["id"]
    item_2_id = rfq["line_items"][1]["id"]
    print(f"RFQ created: {rfq_id}")

    print("\n=== Step 2: Ingesting Quotations for Suppliers ===")
    with open("/app/tests/fixtures/quotations/clean_bearings.csv", "rb") as f:
        csv_content = f.read()
    
    # Supplier Alpha (Cheaper, faster -> Rank 1)
    q_alpha = httpx.post(f"{BASE_URL}/quotations", json={"rfq_id": rfq_id, "supplier_name": "Supplier Alpha"}, headers=HEADERS).json()
    qid_a = q_alpha["id"]
    httpx.post(f"{BASE_URL}/quotations/{qid_a}/documents", files={"file": ("alpha.csv", csv_content, "text/csv")}, headers=HEADERS)
    httpx.post(f"{BASE_URL}/quotations/{qid_a}/extract", headers=HEADERS)
    extr_a = wait_for_extraction(qid_a)
    httpx.patch(f"{BASE_URL}/quotations/{qid_a}/line-items/{extr_a['line_items'][0]['id']}", json={
        "rfq_line_item_id": item_1_id, "unit_price": 10.0, "quantity": 100, "total_price": 1000.0, "currency": "USD", "lead_time_days": 10
    }, headers=HEADERS)
    httpx.patch(f"{BASE_URL}/quotations/{qid_a}/line-items/{extr_a['line_items'][1]['id']}", json={
        "rfq_line_item_id": item_2_id, "unit_price": 5.0, "quantity": 50, "total_price": 250.0, "currency": "USD", "lead_time_days": 10
    }, headers=HEADERS)
    if len(extr_a["line_items"]) > 2:
        httpx.delete(f"{BASE_URL}/quotations/{qid_a}/line-items/{extr_a['line_items'][2]['id']}", headers=HEADERS)
    httpx.post(f"{BASE_URL}/quotations/{qid_a}/review-decision", json={"status": "approved", "decision_notes": "Approved Alpha"}, headers=HEADERS)

    # Supplier Beta (More expensive -> Rank 2)
    q_beta = httpx.post(f"{BASE_URL}/quotations", json={"rfq_id": rfq_id, "supplier_name": "Supplier Beta"}, headers=HEADERS).json()
    qid_b = q_beta["id"]
    httpx.post(f"{BASE_URL}/quotations/{qid_b}/documents", files={"file": ("beta.csv", csv_content, "text/csv")}, headers=HEADERS)
    httpx.post(f"{BASE_URL}/quotations/{qid_b}/extract", headers=HEADERS)
    extr_b = wait_for_extraction(qid_b)
    httpx.patch(f"{BASE_URL}/quotations/{qid_b}/line-items/{extr_b['line_items'][0]['id']}", json={
        "rfq_line_item_id": item_1_id, "unit_price": 15.0, "quantity": 100, "total_price": 1500.0, "currency": "USD", "lead_time_days": 20
    }, headers=HEADERS)
    httpx.patch(f"{BASE_URL}/quotations/{qid_b}/line-items/{extr_b['line_items'][1]['id']}", json={
        "rfq_line_item_id": item_2_id, "unit_price": 8.0, "quantity": 50, "total_price": 400.0, "currency": "USD", "lead_time_days": 20
    }, headers=HEADERS)
    if len(extr_b["line_items"]) > 2:
        httpx.delete(f"{BASE_URL}/quotations/{qid_b}/line-items/{extr_b['line_items'][2]['id']}", headers=HEADERS)
    httpx.post(f"{BASE_URL}/quotations/{qid_b}/review-decision", json={"status": "approved", "decision_notes": "Approved Beta"}, headers=HEADERS)

    print("Suppliers Alpha and Beta ingested and approved.")

    print("\n=== Step 3: ComparisonSnapshot and ScoringConfiguration ===")
    snap_resp = httpx.post(f"{BASE_URL}/rfqs/{rfq_id}/matrix/snapshots", json={"title": "Docker Gate Snapshot"}, headers=HEADERS)
    assert snap_resp.status_code == 201
    snapshot_id = snap_resp.json()["id"]

    config_payload = {
        "name": "Docker Gate Config",
        "description": "60/40 price/lead_time",
        "criteria": [
            {"criterion_id": "c-price", "name": "Total Price", "weight": 0.6000, "direction": "lower_is_better", "source_type": "price", "source_field": "normalized_comparable_total"},
            {"criterion_id": "c-lead-time", "name": "Overall Lead Time", "weight": 0.4000, "direction": "lower_is_better", "source_type": "lead_time", "source_field": "overall_lead_time_days"},
        ],
        "normalization_method": "min_max",
        "missing_value_policy": "block_scoring",
        "tie_policy": "standard_competitive",
        "engine_version": "1.0",
    }
    cfg_resp = httpx.post(f"{BASE_URL}/rfqs/{rfq_id}/scoring/configurations", json=config_payload, headers=HEADERS)
    assert cfg_resp.status_code == 201
    config_id = cfg_resp.json()["id"]

    print("\n=== Step 4: Authoritative ScoringRun ===")
    run_resp = httpx.post(f"{BASE_URL}/rfqs/{rfq_id}/scoring/runs", json={
        "configuration_id": config_id,
        "snapshot_id": snapshot_id,
        "name": "Docker Gate Scoring Run #1",
    }, headers=HEADERS)
    assert run_resp.status_code == 201
    run_data = run_resp.json()
    scoring_run_id_1 = run_data["id"]
    suppliers = run_data["results_payload"]["suppliers"]
    rank1_s = next(s for s in suppliers if s["rank"] == 1)
    rank2_s = next(s for s in suppliers if s["rank"] == 2)
    print(f"ScoringRun #1 created: {scoring_run_id_1}")
    print(f"Rank 1: {rank1_s['supplier_name']} (score: {rank1_s['total_score']})")
    print(f"Rank 2: {rank2_s['supplier_name']} (score: {rank2_s['total_score']})")
    assert rank1_s["supplier_name"] == "Supplier Alpha"
    assert rank2_s["supplier_name"] == "Supplier Beta"

    print("\n=== Step 5: DecisionContext & Mock Narrative Generation ===")
    narr_resp = httpx.post(f"{BASE_URL}/rfqs/{rfq_id}/decisions/narratives", json={
        "scoring_run_id": scoring_run_id_1,
        "narrative_type": "decision_support_memo",
        "include_sensitivity": False,
    }, headers=HEADERS)
    assert narr_resp.status_code == 201
    narr_data = narr_resp.json()
    narrative_id = narr_data["id"]
    context_id = narr_data["decision_context_id"]
    print(f"Narrative #{narr_data['generation_number']} created: {narrative_id}")
    print(f"DecisionContext ID: {context_id}")
    print(f"Origin: {narr_data['origin']}, Provider: {narr_data['provider']}")
    assert narr_data["provider"] == "mock"
    assert narr_data["origin"] == "ai_generated"
    assert len(narr_data["claims"]) > 0

    print("\n=== Step 6: Grounded Claim Inspection ===")
    ctx_resp = httpx.get(f"{BASE_URL}/rfqs/{rfq_id}/decisions/contexts/{context_id}", headers=HEADERS)
    assert ctx_resp.status_code == 200
    ctx_data = ctx_resp.json()
    print(f"DecisionContext hash: {ctx_data['context_hash']}")
    claims = narr_data["claims"]
    print(f"Inspecting {len(claims)} claims:")
    for c in claims[:3]:
        print(f" - [{c['claim_type']}] {c['grounding_status']}: '{c['text'][:60]}...'")
    assert narr_data["grounding_validation_result"]["unsupported"] == 0

    print("\n=== Step 7: Human Revision (Append-Only) ===")
    rev_resp = httpx.post(f"{BASE_URL}/rfqs/{rfq_id}/decisions/narratives/{narrative_id}/revisions", json={
        "revised_text": "Executive Procurement Summary: Reviewed and approved by evaluation committee.",
        "revision_rationale": "Clarified committee consensus rationale.",
    }, headers=HEADERS)
    assert rev_resp.status_code == 201
    rev_data = rev_resp.json()
    print(f"Human revision #{rev_data['revision_number']} saved by {rev_data['revised_by']}")

    print("\n=== Step 8: Empty / Invalid Award Selector Rejection ===")
    # Missing supplier ID / invalid format
    bad_award_resp = httpx.post(f"{BASE_URL}/rfqs/{rfq_id}/decisions/awards", json={
        "scoring_run_id": scoring_run_id_1,
        "awarded_supplier_id": "00000000-0000-0000-0000-000000000000",
        "award_justification": "Invalid supplier test",
    }, headers=HEADERS)
    assert bad_award_resp.status_code in (422, 404), f"Expected 422/404 for invalid supplier, got {bad_award_resp.status_code}"
    print(f"Invalid supplier properly rejected with status {bad_award_resp.status_code}")

    print("\n=== Step 9: Rank #2 Selection + Mandatory Rationale Enforcement ===")
    # Attempting Rank #2 without non_rank1_rationale MUST fail with 422
    bad_rank2 = httpx.post(f"{BASE_URL}/rfqs/{rfq_id}/decisions/awards", json={
        "scoring_run_id": scoring_run_id_1,
        "awarded_supplier_id": rank2_s["quotation_id"],
        "narrative_generation_id": narrative_id,
        "award_justification": "Selecting Rank 2 without mandatory rationale",
    }, headers=HEADERS)
    assert bad_rank2.status_code == 422, f"Expected 422 for Rank 2 without rationale, got {bad_rank2.status_code}"
    print("Rank #2 award without rationale rejected with 422 as required.")

    # With mandatory non_rank1_rationale MUST succeed
    good_rank2 = httpx.post(f"{BASE_URL}/rfqs/{rfq_id}/decisions/awards", json={
        "scoring_run_id": scoring_run_id_1,
        "awarded_supplier_id": rank2_s["quotation_id"],
        "narrative_generation_id": narrative_id,
        "non_rank1_rationale": "Supplier Beta is selected due to strategic supplier diversity requirements and local manufacturing footprint.",
        "award_justification": "Strategic business selection approved by committee.",
    }, headers=HEADERS)
    assert good_rank2.status_code == 201, f"Expected 201 for Rank 2 with rationale, got {good_rank2.status_code}"
    award_data = good_rank2.json()
    award_id = award_data["id"]
    print(f"Draft award created for Rank #{award_data['awarded_supplier_rank']}: {award_id}")

    print("\n=== Step 10: Explicit Human Award Confirmation ===")
    confirm_resp = httpx.post(f"{BASE_URL}/rfqs/{rfq_id}/decisions/awards/{award_id}/confirm", json={
        "final_justification": "Formal executive award signoff confirmed.",
    }, headers=HEADERS)
    assert confirm_resp.status_code == 200, f"Expected 200 on confirm, got {confirm_resp.status_code}"
    confirmed = confirm_resp.json()
    assert confirmed["current_status"] == "confirmed"
    assert confirmed["provenance_hash"] is not None
    print(f"Award confirmed! Status: {confirmed['current_status']}, Provenance Hash: {confirmed['provenance_hash'][:16]}...")

    # Check RFQ status transitioned to decided
    rfq_check = httpx.get(f"{BASE_URL}/rfqs/{rfq_id}", headers=HEADERS).json()
    assert rfq_check["status"] == "decided"
    print(f"RFQ {rfq_id} status transitioned to: {rfq_check['status']}")

    print("\n=== Step 11: Timeline / Event Log Inspection ===")
    events = confirmed["events"]
    print(f"Award has {len(events)} events:")
    for ev in events:
        print(f" - Event #{ev['event_number']}: {ev['event_type']} by {ev['actor_principal']}")
    assert any(e["event_type"] == "confirmed" for e in events)

    print("\n=== Step 12: Newer ScoringRun & Superseded Semantics ===")
    run2_resp = httpx.post(f"{BASE_URL}/rfqs/{rfq_id}/scoring/runs", json={
        "configuration_id": config_id,
        "snapshot_id": snapshot_id,
        "name": "Docker Gate Scoring Run #2 (Superseding)",
    }, headers=HEADERS)
    assert run2_resp.status_code == 201
    scoring_run_id_2 = run2_resp.json()["id"]
    print(f"Newer ScoringRun #2 created: {scoring_run_id_2}")

    # Inspect narrative #1
    narr_check = httpx.get(f"{BASE_URL}/rfqs/{rfq_id}/decisions/narratives/{narrative_id}", headers=HEADERS).json()
    print(f"Narrative #{narrative_id} is_superseded: {narr_check['is_superseded']}")
    assert narr_check["is_superseded"] is True
    print(f"Superseded reason: {narr_check['superseded_reason']}")

    # Check award is_based_on_latest_run is now False, but confirmed status remains intact
    award_check = httpx.get(f"{BASE_URL}/rfqs/{rfq_id}/decisions/awards/{award_id}", headers=HEADERS).json()
    print(f"Award #{award_id} status: {award_check['current_status']}, is_based_on_latest_run: {award_check['is_based_on_latest_run']}")
    assert award_check["current_status"] == "confirmed"
    assert award_check["is_based_on_latest_run"] is False

    print("\n=== Step 13: AI-Disabled Decision Workflow Verification ===")
    # Create another RFQ, ingest, score, and perform human award completely WITHOUT narrative generation
    rfq2 = httpx.post(f"{BASE_URL}/rfqs", json={
        "title": "AI-Disabled Human Decision RFQ",
        "category": "Services",
        "reference_currency": "USD",
        "line_items": [{"position": 1, "description": "Consulting", "quantity": 10, "unit": "hrs"}],
        "criteria": [{"name": "Rate", "weight": 1.0, "direction": "lower_is_better", "data_type": "price"}],
    }, headers=HEADERS).json()
    rfq2_id = rfq2["id"]
    
    q_c = httpx.post(f"{BASE_URL}/quotations", json={"rfq_id": rfq2_id, "supplier_name": "Solo Supplier"}, headers=HEADERS).json()
    qid_c = q_c["id"]
    httpx.post(f"{BASE_URL}/quotations/{qid_c}/documents", files={"file": ("c.csv", csv_content, "text/csv")}, headers=HEADERS)
    httpx.post(f"{BASE_URL}/quotations/{qid_c}/extract", headers=HEADERS)
    extr_c = wait_for_extraction(qid_c)
    httpx.patch(f"{BASE_URL}/quotations/{qid_c}/line-items/{extr_c['line_items'][0]['id']}", json={
        "rfq_line_item_id": rfq2["line_items"][0]["id"], "unit_price": 100.0, "quantity": 10, "total_price": 1000.0, "currency": "USD"
    }, headers=HEADERS)
    for extra_item in extr_c["line_items"][1:]:
        httpx.delete(f"{BASE_URL}/quotations/{qid_c}/line-items/{extra_item['id']}", headers=HEADERS)
    httpx.post(f"{BASE_URL}/quotations/{qid_c}/review-decision", json={"status": "approved"}, headers=HEADERS)

    snap2 = httpx.post(f"{BASE_URL}/rfqs/{rfq2_id}/matrix/snapshots", json={"title": "Snapshot"}, headers=HEADERS).json()
    cfg2 = httpx.post(f"{BASE_URL}/rfqs/{rfq2_id}/scoring/configurations", json={
        "name": "Config",
        "criteria": [{"criterion_id": "c-rate", "name": "Rate", "weight": 1.0, "direction": "lower_is_better", "source_type": "price", "source_field": "normalized_comparable_total"}],
        "normalization_method": "min_max",
    }, headers=HEADERS).json()
    run3 = httpx.post(f"{BASE_URL}/rfqs/{rfq2_id}/scoring/runs", json={"configuration_id": cfg2["id"], "snapshot_id": snap2["id"], "name": "Run 1"}, headers=HEADERS).json()

    # Create award directly with narrative_generation_id=None
    ai_free_award = httpx.post(f"{BASE_URL}/rfqs/{rfq2_id}/decisions/awards", json={
        "scoring_run_id": run3["id"],
        "awarded_supplier_id": qid_c,
        "narrative_generation_id": None,
        "award_justification": "Awarded purely via deterministic human decision without AI.",
    }, headers=HEADERS)
    assert ai_free_award.status_code == 201, f"Failed AI-free draft award: {ai_free_award.status_code} {ai_free_award.text}"
    ai_free_award_id = ai_free_award.json()["id"]

    confirm_ai_free = httpx.post(f"{BASE_URL}/rfqs/{rfq2_id}/decisions/awards/{ai_free_award_id}/confirm", json={
        "final_justification": "Confirmed without AI narrative.",
    }, headers=HEADERS)
    assert confirm_ai_free.status_code == 200
    assert confirm_ai_free.json()["current_status"] == "confirmed"
    print("AI-Disabled human award workflow completed successfully!")

    print("\n========================================================")
    print("ALL DOCKER RUNTIME GATE WORKFLOW CHECKS PASSED!")
    print("========================================================")

if __name__ == "__main__":
    run_gate()
