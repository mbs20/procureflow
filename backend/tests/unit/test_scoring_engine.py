from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi import HTTPException

from procureflow.schemas.scoring import (
    CriterionConfig,
    CriterionDirection,
    EligibilityStatus,
    ScoringConfigurationCreate,
)
from procureflow.services.scoring_service import ScoringService


@pytest.fixture
def scoring_service() -> ScoringService:
    return ScoringService()


@pytest.fixture
def sample_snapshot_matrix() -> dict:
    """
    Synthetic snapshot matrix data with:
    - 3 eligible suppliers (A, B, C)
    - 1 knockout-failing supplier (D: lead time exceeds threshold)
    - Price, lead time, and Incoterms categorical criteria
    """
    return {
        "suppliers": [
            {
                "quotation_id": "supp-a",
                "supplier_name": "Supplier A",
                "status": "approved",
                "normalized_comparable_total": 10000.00,
                "overall_lead_time_days": 10,
                "incoterms": "DDP",
            },
            {
                "quotation_id": "supp-b",
                "supplier_name": "Supplier B",
                "status": "approved",
                "normalized_comparable_total": 12000.00,
                "overall_lead_time_days": 20,
                "incoterms": "FOB",
            },
            {
                "quotation_id": "supp-c",
                "supplier_name": "Supplier C",
                "status": "approved",
                "normalized_comparable_total": 14000.00,
                "overall_lead_time_days": 15,
                "incoterms": "DAP",
            },
            {
                "quotation_id": "supp-d",
                "supplier_name": "Supplier D (Knockout)",
                "status": "approved",
                "normalized_comparable_total": 8000.00,  # Cheaper, but fails lead time!
                "overall_lead_time_days": 45,  # Exceeds max 30 days
                "incoterms": "DDP",
            },
        ],
        "required_line_items": [],
    }


@pytest.fixture
def sample_scoring_config() -> ScoringConfigurationCreate:
    return ScoringConfigurationCreate(
        name="Production Evaluation Model v1",
        description="Standard 3-criteria evaluation model",
        criteria=[
            CriterionConfig(
                criterion_id="crit-price",
                name="Total Price",
                weight=Decimal("0.5000"),
                direction=CriterionDirection.LOWER_IS_BETTER,
                source_type="price",
                source_field="normalized_comparable_total",
            ),
            CriterionConfig(
                criterion_id="crit-lead-time",
                name="Lead Time (Days)",
                weight=Decimal("0.3000"),
                direction=CriterionDirection.LOWER_IS_BETTER,
                source_type="lead_time",
                source_field="overall_lead_time_days",
                is_knockout=True,
                knockout_threshold=Decimal("30"),
            ),
            CriterionConfig(
                criterion_id="crit-incoterms",
                name="Commercial Incoterms",
                weight=Decimal("0.2000"),
                direction=CriterionDirection.HIGHER_IS_BETTER,
                source_type="incoterms",
                source_field="incoterms",
                categorical_map={
                    "DDP": Decimal("100"),
                    "DAP": Decimal("75"),
                    "FOB": Decimal("40"),
                    "EXW": Decimal("10"),
                },
            ),
        ],
    )


def test_scoring_knockout_precedence_and_min_max_isolation(
    scoring_service: ScoringService,
    sample_snapshot_matrix: dict,
    sample_scoring_config: ScoringConfigurationCreate,
):
    """
    Suppliers failing knockout must:
    1. Receive KNOCKOUT_FAILED eligibility status with reason recorded.
    2. Be strictly excluded from the min/max extremes calculation of eligible suppliers.
       (e.g., Supplier D's $8,000 price must NOT be the min price; Supplier A's $10,000 must be min).
    """
    scores = scoring_service.evaluate_scoring(sample_snapshot_matrix, sample_scoring_config)

    supp_d = next(s for s in scores if s.quotation_id == "supp-d")
    assert supp_d.eligibility_status == EligibilityStatus.KNOCKOUT_FAILED
    assert supp_d.rank is None
    assert any("exceeds maximum knockout threshold 30" in r for r in supp_d.knockout_reasons)

    # Check eligible cohort
    eligible = [s for s in scores if s.eligibility_status == EligibilityStatus.ELIGIBLE]
    assert len(eligible) == 3

    # Check price extremes in Supplier A breakdown
    supp_a = next(s for s in eligible if s.quotation_id == "supp-a")
    price_breakdown = next(b for b in supp_a.criteria_breakdown if b.criterion_id == "crit-price")
    # Min price should be 10,000 (from A), Max price should be 14,000 (from C)
    assert price_breakdown.min_value == Decimal("10000.00")
    assert price_breakdown.max_value == Decimal("14000.00")

    # Supplier A price: (14,000 - 10,000) / (14,000 - 10,000) * 100 = 100.00
    assert price_breakdown.normalized_score == Decimal("100.0000")
    # Weighted contribution: 100.00 * 0.50 = 50.00
    assert price_breakdown.weighted_contribution == Decimal("50.0000")


def test_exact_mathematical_score_breakdown(
    scoring_service: ScoringService,
    sample_snapshot_matrix: dict,
    sample_scoring_config: ScoringConfigurationCreate,
):
    """
    Verify exact Decimal scoring calculation for Supplier A:
    - Price: 10,000 -> 100.00 score -> 50.00 contribution (50% weight)
    - Lead Time: 10 days -> min=10, max=20 -> (20 - 10)/(20 - 10)*100 = 100.00 -> 30.00 contribution (30% weight)
    - Incoterms: DDP -> 100 utility -> min=40 (FOB), max=100 (DDP) -> (100 - 40)/(100 - 40)*100 = 100.00 -> 20.00 contribution (20% weight)
    - Total: 50.00 + 30.00 + 20.00 = 100.00, Rank 1.
    """
    scores = scoring_service.evaluate_scoring(sample_snapshot_matrix, sample_scoring_config)
    supp_a = next(s for s in scores if s.quotation_id == "supp-a")
    assert supp_a.total_score == Decimal("100.0000")
    assert supp_a.rank == 1

    # Supplier B:
    # Price: 12,000 -> (14,000 - 12,000)/(14,000 - 10,000)*100 = 50.00 -> 25.00 contrib
    # Lead Time: 20 days -> (20 - 20)/(20 - 10)*100 = 0.00 -> 0.00 contrib
    # Incoterms: FOB (40) -> (40 - 40)/(100 - 40)*100 = 0.00 -> 0.00 contrib
    # Total: 25.00
    supp_b = next(s for s in scores if s.quotation_id == "supp-b")
    assert supp_b.total_score == Decimal("25.0000")
    assert supp_b.rank == 3

    # Supplier C:
    # Price: 14,000 -> 0.00 score -> 0.00 contrib
    # Lead Time: 15 days -> (20 - 15)/10 * 100 = 50.00 -> 15.00 contrib
    # Incoterms: DAP (75) -> (75 - 40)/(100 - 40)*100 = 35/60 * 100 = 58.3333 -> 11.6667 contrib
    # Total: 26.6667, Rank 2
    supp_c = next(s for s in scores if s.quotation_id == "supp-c")
    assert supp_c.total_score == Decimal("26.6667")
    assert supp_c.rank == 2


def test_tied_supplier_ranking_preservation(scoring_service: ScoringService):
    """
    Standard competitive ranking (1, 1, 3) must be preserved for exact score ties.
    """
    matrix = {
        "suppliers": [
            {"quotation_id": "s1", "supplier_name": "Supplier 1", "val": 100},
            {"quotation_id": "s2", "supplier_name": "Supplier 2", "val": 100},
            {"quotation_id": "s3", "supplier_name": "Supplier 3", "val": 200},
        ]
    }
    cfg = ScoringConfigurationCreate(
        name="Tie Test",
        criteria=[
            CriterionConfig(
                criterion_id="c1",
                name="Val",
                weight=Decimal("1.0000"),
                direction=CriterionDirection.LOWER_IS_BETTER,
                source_type="custom",
                source_field="val",
            )
        ],
    )
    scores = scoring_service.evaluate_scoring(matrix, cfg)
    s1 = next(s for s in scores if s.quotation_id == "s1")
    s2 = next(s for s in scores if s.quotation_id == "s2")
    s3 = next(s for s in scores if s.quotation_id == "s3")

    assert s1.total_score == Decimal("100.0000")
    assert s2.total_score == Decimal("100.0000")
    assert s1.rank == 1
    assert s2.rank == 1
    assert s3.rank == 3


def test_zero_variance_and_single_supplier_gives_full_score(scoring_service: ScoringService):
    """
    When min == max across eligible suppliers (or single supplier), score is 100.00.
    """
    matrix = {
        "suppliers": [
            {"quotation_id": "s1", "supplier_name": "Single Supplier", "val": 500},
        ]
    }
    cfg = ScoringConfigurationCreate(
        name="Single Supplier Test",
        criteria=[
            CriterionConfig(
                criterion_id="c1",
                name="Val",
                weight=Decimal("1.0000"),
                direction=CriterionDirection.LOWER_IS_BETTER,
                source_type="custom",
                source_field="val",
            )
        ],
    )
    scores = scoring_service.evaluate_scoring(matrix, cfg)
    assert len(scores) == 1
    assert scores[0].total_score == Decimal("100.0000")
    assert scores[0].rank == 1


def test_missing_value_policy_blocks_scoring(
    scoring_service: ScoringService,
    sample_scoring_config: ScoringConfigurationCreate,
):
    """
    If an eligible supplier lacks a required criterion or unmapped categorical value,
    BLOCK_SCORING policy must raise an explicit HTTP 422 exception.
    """
    matrix_with_unmapped = {
        "suppliers": [
            {
                "quotation_id": "s1",
                "supplier_name": "Supplier 1",
                "normalized_comparable_total": 10000.00,
                "overall_lead_time_days": 10,
                "incoterms": "UNKNOWN_TERM",  # Not in categorical_map!
            }
        ]
    }
    with pytest.raises(HTTPException) as exc_info:
        scoring_service.evaluate_scoring(matrix_with_unmapped, sample_scoring_config)

    assert exc_info.value.status_code == 422
    assert "not mapped in criterion" in str(exc_info.value.detail)


def test_sensitivity_proportional_weight_redistribution(
    scoring_service: ScoringService,
    sample_scoring_config: ScoringConfigurationCreate,
):
    """
    When swept criterion changes from 0.50 to 0.70:
    - crit-price becomes 0.70
    - Remaining pool: 1.00 - 0.70 = 0.30
    - Unlocked criteria: crit-lead-time (0.30) and crit-incoterms (0.20), ratio = 3:2
    - crit-lead-time becomes 0.30 * (0.3 / 0.5) = 0.18
    - crit-incoterms becomes 0.30 * (0.2 / 0.5) = 0.12
    - Total sum remains exactly 1.0000
    """
    redistributed = scoring_service.redistribute_weights(
        base_criteria=sample_scoring_config.criteria,
        swept_cid="crit-price",
        new_weight=Decimal("0.7000"),
        locked_cids=[],
    )
    assert sum(c.weight for c in redistributed) == Decimal("1.0000")

    p_crit = next(c for c in redistributed if c.criterion_id == "crit-price")
    lt_crit = next(c for c in redistributed if c.criterion_id == "crit-lead-time")
    inco_crit = next(c for c in redistributed if c.criterion_id == "crit-incoterms")

    assert p_crit.weight == Decimal("0.7000")
    assert lt_crit.weight == Decimal("0.1800")
    assert inco_crit.weight == Decimal("0.1200")


def test_bisection_breakeven_mathematical_precision(
    scoring_service: ScoringService,
    sample_snapshot_matrix: dict,
    sample_scoring_config: ScoringConfigurationCreate,
):
    """
    Supplier C is currently Rank 2 (Total $14,000, score 26.67).
    Supplier A is Rank 1 (Total $10,000, score 100.00).
    Test bisection breakeven search for Supplier C to reach Rank 1:
    - Recomputes full cohort at each step.
    - Accurately identifies candidate crossing min price ($10,000) because Supplier A has 100 in other criteria.
    - Demonstrates convergence to within tolerance.
    """
    result = scoring_service.compute_bisection_breakeven(
        snapshot_matrix_data=sample_snapshot_matrix,
        config=sample_scoring_config,
        candidate_id="supp-c",
        target_rank=1,
        tolerance=Decimal("0.01"),
    )
    assert result.feasible is True
    assert result.candidate_id == "supp-c"
    assert result.current_price == Decimal("14000.00")
    assert result.required_price is not None
    assert result.required_price < Decimal(
        "10000.00"
    )  # Must be cheaper than A because A leads in lead time & Incoterms!
    assert result.delta_price is not None and result.delta_price > Decimal("0.00")
    assert result.convergence_steps > 0
    assert result.convergence_steps <= 50


def test_bisection_breakeven_infeasible_when_disqualified(
    scoring_service: ScoringService,
    sample_snapshot_matrix: dict,
    sample_scoring_config: ScoringConfigurationCreate,
):
    """
    Supplier D is disqualified due to knockout rule.
    Breakeven must immediately declare infeasible and not run search.
    """
    result = scoring_service.compute_bisection_breakeven(
        snapshot_matrix_data=sample_snapshot_matrix,
        config=sample_scoring_config,
        candidate_id="supp-d",
        target_rank=1,
    )
    assert result.feasible is False
    assert "failed knockout criteria" in result.notes
