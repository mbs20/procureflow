from __future__ import annotations

import json
from decimal import Decimal

import pytest

from procureflow.services.scoring_service import (
    ENGINE_POLICY_METADATA,
    SCORING_ENGINE_VERSION,
    compute_canonical_hash,
    compute_scoring_run_hash,
    verify_scoring_run_integrity,
)


@pytest.fixture
def sample_snapshot_data() -> dict:
    return {
        "suppliers": [
            {
                "quotation_id": "supp-a",
                "supplier_name": "Supplier A",
                "normalized_comparable_total": 10000.00,
            },
            {
                "quotation_id": "supp-b",
                "supplier_name": "Supplier B",
                "normalized_comparable_total": 12000.00,
            },
        ]
    }


@pytest.fixture
def sample_config_data() -> dict:
    return {
        "name": "Phase 5 Model",
        "criteria": [
            {
                "criterion_id": "crit-price",
                "name": "Price",
                "weight": "1.0000",
                "direction": "lower_is_better",
            }
        ],
    }


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
                    "max_value": Decimal("12000.00"),
                    "exact_min_value": "10000.00",
                    "exact_max_value": "12000.00",
                    "normalized_score": Decimal("100.0000"),
                    "exact_normalized_score": "100.0000000000",
                    "weight": Decimal("1.0000"),
                    "weighted_contribution": Decimal("100.0000"),
                    "exact_weighted_contribution": "100.0000000000",
                    "is_knockout_applied": False,
                }
            ],
        },
        {
            "quotation_id": "supp-b",
            "supplier_name": "Supplier B",
            "eligibility_status": "eligible",
            "knockout_reasons": [],
            "total_score": Decimal("0.0000"),
            "exact_total_score": "0.0000000000",
            "rank": 2,
            "criteria_breakdown": [
                {
                    "criterion_id": "crit-price",
                    "criterion_name": "Price",
                    "raw_value": 12000.00,
                    "exact_raw_value": "12000.00",
                    "direction": "lower_is_better",
                    "min_value": Decimal("10000.00"),
                    "max_value": Decimal("12000.00"),
                    "exact_min_value": "10000.00",
                    "exact_max_value": "12000.00",
                    "normalized_score": Decimal("0.0000"),
                    "exact_normalized_score": "0.0000000000",
                    "weight": Decimal("1.0000"),
                    "weighted_contribution": Decimal("0.0000"),
                    "exact_weighted_contribution": "0.0000000000",
                    "is_knockout_applied": False,
                }
            ],
        },
    ]


def test_provenance_hash_deterministic_identical_inputs(
    sample_snapshot_data: dict, sample_config_data: dict, sample_suppliers_payload: list[dict]
):
    """
    Identical immutable inputs must always produce the exact same SHA-256 hash.
    """
    snap_hash = compute_canonical_hash(sample_snapshot_data)
    cfg_hash = compute_canonical_hash(sample_config_data)

    hash1 = compute_scoring_run_hash(
        rfq_id="rfq-123",
        snapshot_id="snap-1",
        snapshot_version=1,
        comparison_snapshot_hash=snap_hash,
        configuration_id="cfg-1",
        configuration_version=1,
        scoring_configuration_hash=cfg_hash,
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
        comparison_snapshot_hash=snap_hash,
        configuration_id="cfg-1",
        configuration_version=1,
        scoring_configuration_hash=cfg_hash,
        engine_version=SCORING_ENGINE_VERSION,
        engine_policy=ENGINE_POLICY_METADATA,
        eligible_suppliers_count=2,
        knockout_suppliers_count=0,
        suppliers=sample_suppliers_payload,
    )
    assert hash1 == hash2
    assert len(hash1) == 64


def test_provenance_hash_changes_when_snapshot_content_changes_same_id(
    sample_snapshot_data: dict, sample_config_data: dict, sample_suppliers_payload: list[dict]
):
    """
    Modifying snapshot matrix data content while retaining the exact same snapshot ID
    MUST produce a different hash and fail verification.
    """
    snap_hash_original = compute_canonical_hash(sample_snapshot_data)
    cfg_hash = compute_canonical_hash(sample_config_data)

    run_hash = compute_scoring_run_hash(
        rfq_id="rfq-123",
        snapshot_id="snap-1",
        snapshot_version=1,
        comparison_snapshot_hash=snap_hash_original,
        configuration_id="cfg-1",
        configuration_version=1,
        scoring_configuration_hash=cfg_hash,
        engine_version=SCORING_ENGINE_VERSION,
        engine_policy=ENGINE_POLICY_METADATA,
        eligible_suppliers_count=2,
        knockout_suppliers_count=0,
        suppliers=sample_suppliers_payload,
    )

    results_payload = {
        "rfq_id": "rfq-123",
        "snapshot_id": "snap-1",
        "snapshot_version": 1,
        "comparison_snapshot_hash": snap_hash_original,
        "configuration_id": "cfg-1",
        "configuration_version": 1,
        "scoring_configuration_hash": cfg_hash,
        "engine_version": SCORING_ENGINE_VERSION,
        "engine_policy": ENGINE_POLICY_METADATA,
        "provenance_hash": run_hash,
        "eligible_suppliers_count": 2,
        "knockout_suppliers_count": 0,
        "suppliers": sample_suppliers_payload,
    }

    # 1. Matching snapshot content succeeds
    assert (
        verify_scoring_run_integrity(
            results_payload,
            snapshot_matrix_data=sample_snapshot_data,
            config_payload=sample_config_data,
        )
        is True
    )

    # 2. Mutated snapshot content (e.g. price altered from 10000 to 9000) fails verification
    mutated_snapshot = json.loads(json.dumps(sample_snapshot_data))
    mutated_snapshot["suppliers"][0]["normalized_comparable_total"] = 9000.00
    assert (
        verify_scoring_run_integrity(
            results_payload,
            snapshot_matrix_data=mutated_snapshot,
            config_payload=sample_config_data,
        )
        is False
    )


def test_provenance_hash_changes_when_configuration_content_changes_same_id(
    sample_snapshot_data: dict, sample_config_data: dict, sample_suppliers_payload: list[dict]
):
    """
    Modifying scoring configuration content (e.g. direction or weight) while retaining the exact same
    configuration ID MUST produce a different hash and fail verification.
    """
    snap_hash = compute_canonical_hash(sample_snapshot_data)
    cfg_hash_original = compute_canonical_hash(sample_config_data)

    run_hash = compute_scoring_run_hash(
        rfq_id="rfq-123",
        snapshot_id="snap-1",
        snapshot_version=1,
        comparison_snapshot_hash=snap_hash,
        configuration_id="cfg-1",
        configuration_version=1,
        scoring_configuration_hash=cfg_hash_original,
        engine_version=SCORING_ENGINE_VERSION,
        engine_policy=ENGINE_POLICY_METADATA,
        eligible_suppliers_count=2,
        knockout_suppliers_count=0,
        suppliers=sample_suppliers_payload,
    )

    results_payload = {
        "rfq_id": "rfq-123",
        "snapshot_id": "snap-1",
        "snapshot_version": 1,
        "comparison_snapshot_hash": snap_hash,
        "configuration_id": "cfg-1",
        "configuration_version": 1,
        "scoring_configuration_hash": cfg_hash_original,
        "engine_version": SCORING_ENGINE_VERSION,
        "engine_policy": ENGINE_POLICY_METADATA,
        "provenance_hash": run_hash,
        "eligible_suppliers_count": 2,
        "knockout_suppliers_count": 0,
        "suppliers": sample_suppliers_payload,
    }

    # 1. Matching config succeeds
    assert (
        verify_scoring_run_integrity(
            results_payload,
            snapshot_matrix_data=sample_snapshot_data,
            config_payload=sample_config_data,
        )
        is True
    )

    # 2. Mutated config content (e.g. direction changed to higher_is_better) fails verification
    mutated_config = json.loads(json.dumps(sample_config_data))
    mutated_config["criteria"][0]["direction"] = "higher_is_better"
    assert (
        verify_scoring_run_integrity(
            results_payload,
            snapshot_matrix_data=sample_snapshot_data,
            config_payload=mutated_config,
        )
        is False
    )


def test_provenance_hash_tamper_verification(
    sample_snapshot_data: dict, sample_config_data: dict, sample_suppliers_payload: list[dict]
):
    """
    Modifying a frozen score, rank, or breakdown in results_payload must cause
    verify_scoring_run_integrity to return False.
    """
    snap_hash = compute_canonical_hash(sample_snapshot_data)
    cfg_hash = compute_canonical_hash(sample_config_data)

    run_hash = compute_scoring_run_hash(
        rfq_id="rfq-123",
        snapshot_id="snap-1",
        snapshot_version=1,
        comparison_snapshot_hash=snap_hash,
        configuration_id="cfg-1",
        configuration_version=1,
        scoring_configuration_hash=cfg_hash,
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
        "comparison_snapshot_hash": snap_hash,
        "configuration_id": "cfg-1",
        "configuration_version": 1,
        "scoring_configuration_hash": cfg_hash,
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
    tampered_payload["suppliers"][0]["rank"] = 2
    assert verify_scoring_run_integrity(tampered_payload) is False

    # 3. Tampered score in supplier payload
    tampered_score_payload = json.loads(json.dumps(valid_payload, default=str))
    tampered_score_payload["suppliers"][0]["exact_total_score"] = "99.9999000000"
    assert verify_scoring_run_integrity(tampered_score_payload) is False
