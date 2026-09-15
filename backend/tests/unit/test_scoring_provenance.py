from __future__ import annotations

import json
from decimal import Decimal

import pytest

from procureflow.services.scoring_service import (
    ENGINE_POLICY_METADATA,
    SCORING_ENGINE_VERSION,
    compute_scoring_run_hash,
    verify_scoring_run_integrity,
)


@pytest.fixture
def sample_suppliers_payload() -> list[dict]:
    return [
        {
            "quotation_id": "supp-a",
            "supplier_name": "Supplier A",
            "eligibility_status": "eligible",
            "knockout_reasons": [],
            "total_score": Decimal("100.0000"),
            "exact_total_score": "100.0000000000",
            "rank": 1,
            "criteria_breakdown": [
                {
                    "criterion_id": "crit-price",
                    "criterion_name": "Price",
                    "raw_value": 10000.00,
                    "exact_raw_value": "10000.00",
                    "direction": "lower_is_better",
                    "min_value": Decimal("10000.00"),
                    "max_value": Decimal("14000.00"),
                    "exact_min_value": "10000.00",
                    "exact_max_value": "14000.00",
                    "normalized_score": Decimal("100.0000"),
                    "exact_normalized_score": "100.0000000000",
                    "weight": Decimal("0.5000"),
                    "weighted_contribution": Decimal("50.0000"),
                    "exact_weighted_contribution": "50.0000000000",
                    "is_knockout_applied": False,
                }
            ],
        },
        {
            "quotation_id": "supp-b",
            "supplier_name": "Supplier B",
            "eligibility_status": "eligible",
            "knockout_reasons": [],
            "total_score": Decimal("50.0000"),
            "exact_total_score": "50.0000000000",
            "rank": 2,
            "criteria_breakdown": [
                {
                    "criterion_id": "crit-price",
                    "criterion_name": "Price",
                    "raw_value": 12000.00,
                    "exact_raw_value": "12000.00",
                    "direction": "lower_is_better",
                    "min_value": Decimal("10000.00"),
                    "max_value": Decimal("14000.00"),
                    "exact_min_value": "10000.00",
                    "exact_max_value": "14000.00",
                    "normalized_score": Decimal("50.0000"),
                    "exact_normalized_score": "50.0000000000",
                    "weight": Decimal("0.5000"),
                    "weighted_contribution": Decimal("25.0000"),
                    "exact_weighted_contribution": "25.0000000000",
                    "is_knockout_applied": False,
                }
            ],
        },
    ]


def test_provenance_hash_deterministic_identical_inputs(sample_suppliers_payload: list[dict]):
    """
    Identical immutable inputs must always produce the exact same SHA-256 hash.
    """
    hash1 = compute_scoring_run_hash(
        rfq_id="rfq-123",
        snapshot_id="snap-1",
        snapshot_version=1,
        configuration_id="cfg-1",
        configuration_version=1,
        engine_version=SCORING_ENGINE_VERSION,
        engine_policy=ENGINE_POLICY_METADATA,
        eligible_suppliers_count=2,
        knockout_suppliers_count=0,
        suppliers=sample_suppliers_payload,
    )
    hash2 = compute_scoring_run_hash(
        rfq_id="rfq-123",
        snapshot_id="snap-1",
        snapshot_version=1,
        configuration_id="cfg-1",
        configuration_version=1,
        engine_version=SCORING_ENGINE_VERSION,
        engine_policy=ENGINE_POLICY_METADATA,
        eligible_suppliers_count=2,
        knockout_suppliers_count=0,
        suppliers=sample_suppliers_payload,
    )
    assert hash1 == hash2
    assert len(hash1) == 64  # Valid SHA-256 hex string


def test_provenance_hash_changes_when_snapshot_changes(sample_suppliers_payload: list[dict]):
    """
    Changing ComparisonSnapshot ID or version must produce a different hash.
    """
    base_hash = compute_scoring_run_hash(
        rfq_id="rfq-123",
        snapshot_id="snap-1",
        snapshot_version=1,
        configuration_id="cfg-1",
        configuration_version=1,
        engine_version=SCORING_ENGINE_VERSION,
        engine_policy=ENGINE_POLICY_METADATA,
        eligible_suppliers_count=2,
        knockout_suppliers_count=0,
        suppliers=sample_suppliers_payload,
    )
    changed_snap_hash = compute_scoring_run_hash(
        rfq_id="rfq-123",
        snapshot_id="snap-2",  # Changed!
        snapshot_version=2,
        configuration_id="cfg-1",
        configuration_version=1,
        engine_version=SCORING_ENGINE_VERSION,
        engine_policy=ENGINE_POLICY_METADATA,
        eligible_suppliers_count=2,
        knockout_suppliers_count=0,
        suppliers=sample_suppliers_payload,
    )
    assert base_hash != changed_snap_hash


def test_provenance_hash_changes_when_configuration_changes(sample_suppliers_payload: list[dict]):
    """
    Changing ScoringConfiguration ID or version must produce a different hash.
    """
    base_hash = compute_scoring_run_hash(
        rfq_id="rfq-123",
        snapshot_id="snap-1",
        snapshot_version=1,
        configuration_id="cfg-1",
        configuration_version=1,
        engine_version=SCORING_ENGINE_VERSION,
        engine_policy=ENGINE_POLICY_METADATA,
        eligible_suppliers_count=2,
        knockout_suppliers_count=0,
        suppliers=sample_suppliers_payload,
    )
    changed_cfg_hash = compute_scoring_run_hash(
        rfq_id="rfq-123",
        snapshot_id="snap-1",
        snapshot_version=1,
        configuration_id="cfg-2",  # Changed!
        configuration_version=2,
        engine_version=SCORING_ENGINE_VERSION,
        engine_policy=ENGINE_POLICY_METADATA,
        eligible_suppliers_count=2,
        knockout_suppliers_count=0,
        suppliers=sample_suppliers_payload,
    )
    assert base_hash != changed_cfg_hash


def test_provenance_hash_tamper_verification(sample_suppliers_payload: list[dict]):
    """
    Modifying a frozen score, rank, or breakdown in results_payload must cause
    verify_scoring_run_integrity to return False.
    """
    run_hash = compute_scoring_run_hash(
        rfq_id="rfq-123",
        snapshot_id="snap-1",
        snapshot_version=1,
        configuration_id="cfg-1",
        configuration_version=1,
        engine_version=SCORING_ENGINE_VERSION,
        engine_policy=ENGINE_POLICY_METADATA,
        eligible_suppliers_count=2,
        knockout_suppliers_count=0,
        suppliers=sample_suppliers_payload,
    )

    valid_payload = {
        "rfq_id": "rfq-123",
        "snapshot_id": "snap-1",
        "snapshot_version": 1,
        "configuration_id": "cfg-1",
        "configuration_version": 1,
        "engine_version": SCORING_ENGINE_VERSION,
        "engine_policy": ENGINE_POLICY_METADATA,
        "provenance_hash": run_hash,
        "eligible_suppliers_count": 2,
        "knockout_suppliers_count": 0,
        "suppliers": sample_suppliers_payload,
    }

    # 1. Valid payload must verify True
    assert verify_scoring_run_integrity(valid_payload) is True

    # 2. Tampered rank in supplier payload
    tampered_payload = json.loads(json.dumps(valid_payload, default=str))
    tampered_payload["suppliers"][0]["rank"] = 2  # Tampered!
    assert verify_scoring_run_integrity(tampered_payload) is False

    # 3. Tampered score in supplier payload
    tampered_score_payload = json.loads(json.dumps(valid_payload, default=str))
    tampered_score_payload["suppliers"][0]["exact_total_score"] = "99.9999000000"  # Tampered!
    assert verify_scoring_run_integrity(tampered_score_payload) is False
