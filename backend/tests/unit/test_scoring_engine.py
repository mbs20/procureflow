from __future__ import annotations

from decimal import Decimal

import pytest

from procureflow.schemas.scoring import (
    CriterionConfig,
    CriterionDirection,
    EligibilityStatus,
    ScoringConfigurationCreate,
)
from procureflow.services.scoring_service import (
    ENGINE_POLICY_METADATA,
    MissingValueError,
    ScoringService,
    SensitivityConstraintError,
)


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
                "normalized_comparable_total": 8000.00,
                "overall_lead_time_days": 45,
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


# --------------------------------------------------------------------------
# 1. DECIMAL PRECISION & UNROUNDED RANKING REGRESSION TESTS
# --------------------------------------------------------------------------


def test_authoritative_full_decimal_precision_prevents_false_ties_and_rank_inversion(
    scoring_service: ScoringService,
):
    """
    Two suppliers whose total scores differ only beyond standard 4DP/2DP display precision
    (e.g., Supplier 1 has 50.00004, Supplier 2 has 50.00006).
    Display precision will show 50.0000 for both, but authoritative ranking MUST rank Supplier 2 as #1
    and Supplier 1 as #2 without a false tie or rank inversion.
    """
    matrix = {
        "suppliers": [
            {"quotation_id": "supp-1", "supplier_name": "Supplier 1", "score_val": "50.00004"},
            {"quotation_id": "supp-2", "supplier_name": "Supplier 2", "score_val": "50.00006"},
            {"quotation_id": "supp-3", "supplier_name": "Supplier 3", "score_val": "10.00000"},
        ]
    }
    cfg = ScoringConfigurationCreate(
        name="Precision Regression Model",
        criteria=[
            CriterionConfig(
                criterion_id="crit-val",
                name="Score Value",
                weight=Decimal("1.0000"),
                direction=CriterionDirection.HIGHER_IS_BETTER,
                source_type="custom",
                source_field="score_val",
            )
        ],
    )
    scores = scoring_service.evaluate_scoring(matrix, cfg)
    s1 = next(s for s in scores if s.quotation_id == "supp-1")
    s2 = next(s for s in scores if s.quotation_id == "supp-2")
    s3 = next(s for s in scores if s.quotation_id == "supp-3")

    # Authoritative rank comparison proves unrounded comparison
    assert s2.rank == 1
    assert s1.rank == 2
    assert s3.rank == 3

    # Exact strings retain authoritative precision
    assert s1.exact_total_score != s2.exact_total_score
    assert Decimal(s2.exact_total_score) > Decimal(s1.exact_total_score)

    # Display total scores are safely quantized without mutating ranking
    assert s1.total_score == Decimal("100.0000")  # s2 is 100, s1 is (50.00004-10)/(50.00006-10)*100 = 99.99995... -> 100.0000


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

    supp_b = next(s for s in scores if s.quotation_id == "supp-b")
    assert supp_b.total_score == Decimal("25.0000")
    assert supp_b.rank == 3

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
    BLOCK_SCORING policy must raise an explicit MissingValueError.
    """
    matrix_with_unmapped = {
        "suppliers": [
            {
                "quotation_id": "s1",
                "supplier_name": "Supplier 1",
                "normalized_comparable_total": 10000.00,
                "overall_lead_time_days": 10,
                "incoterms": "UNKNOWN_TERM",
            }
        ]
    }
    with pytest.raises(MissingValueError) as exc_info:
        scoring_service.evaluate_scoring(matrix_with_unmapped, sample_scoring_config)

    assert "not mapped in criterion" in str(exc_info.value)


# --------------------------------------------------------------------------
# 2. BREAKEVEN BOUNDARY & BISECTION HARDENING TESTS
# --------------------------------------------------------------------------


def test_breakeven_candidate_between_cohort_min_max(scoring_service: ScoringService):
    """
    Scenario 1: Candidate price remains between existing cohort min and max to achieve target rank #2.
    """
    matrix = {
        "suppliers": [
            {"quotation_id": "s1", "supplier_name": "Supplier 1", "price": 100, "quality": 100},
            {"quotation_id": "s2", "supplier_name": "Supplier 2", "price": 150, "quality": 50},
            {"quotation_id": "s3", "supplier_name": "Candidate", "price": 200, "quality": 50},
        ]
    }
    cfg = ScoringConfigurationCreate(
        name="Breakeven Between Min Max",
        criteria=[
            CriterionConfig(
                criterion_id="c-price",
                name="Price",
                weight=Decimal("0.5000"),
                direction=CriterionDirection.LOWER_IS_BETTER,
                source_type="price",
                source_field="price",
            ),
            CriterionConfig(
                criterion_id="c-qual",
                name="Quality",
                weight=Decimal("0.5000"),
                direction=CriterionDirection.HIGHER_IS_BETTER,
                source_type="custom",
                source_field="quality",
            ),
        ],
    )
    result = scoring_service.compute_bisection_breakeven(
        snapshot_matrix_data=matrix,
        config=cfg,
        candidate_id="s3",
        target_rank=2,
    )
    assert result.feasible is True
    # Required price should be <= 150 (between 100 and 200)
    assert Decimal("100.00") <= result.required_price <= Decimal("150.00")
    assert result.target_rank == 2


def test_breakeven_candidate_crosses_current_min_price(
    scoring_service: ScoringService,
    sample_snapshot_matrix: dict,
    sample_scoring_config: ScoringConfigurationCreate,
):
    """
    Scenario 2: Candidate must cross below existing cohort min ($10,000) to beat Supplier A.
    Every bisection step dynamically updates cohort min price to candidate's simulated price.
    """
    result = scoring_service.compute_bisection_breakeven(
        snapshot_matrix_data=sample_snapshot_matrix,
        config=sample_scoring_config,
        candidate_id="supp-c",
        target_rank=1,
    )
    assert result.feasible is True
    assert result.required_price < Decimal("10000.00")
    assert result.tie_price == result.required_price
    assert result.beat_price < result.required_price
    assert result.target_achievement_type == "tie_or_better"


def test_breakeven_candidate_price_criterion_zero_weight(scoring_service: ScoringService):
    """
    Scenario 3: Price criterion weight is 0.0000. Breakeven must return feasible=False immediately.
    """
    matrix = {
        "suppliers": [
            {"quotation_id": "s1", "supplier_name": "Supplier 1", "price": 100, "quality": 100},
            {"quotation_id": "s2", "supplier_name": "Candidate", "price": 200, "quality": 50},
        ]
    }
    cfg = ScoringConfigurationCreate(
        name="Zero Price Weight",
        criteria=[
            CriterionConfig(
                criterion_id="c-price",
                name="Price",
                weight=Decimal("0.0000"),
                direction=CriterionDirection.LOWER_IS_BETTER,
                source_type="price",
                source_field="price",
            ),
            CriterionConfig(
                criterion_id="c-qual",
                name="Quality",
                weight=Decimal("1.0000"),
                direction=CriterionDirection.HIGHER_IS_BETTER,
                source_type="custom",
                source_field="quality",
            ),
        ],
    )
    result = scoring_service.compute_bisection_breakeven(
        snapshot_matrix_data=matrix,
        config=cfg,
        candidate_id="s2",
        target_rank=1,
    )
    assert result.feasible is False
    assert "0.0000" in result.notes


def test_breakeven_infeasible_at_floor_price(scoring_service: ScoringService):
    """
    Scenario 4: Non-price criteria deficit is too large; even at floor price $0.01, candidate cannot reach rank 1.
    """
    matrix = {
        "suppliers": [
            {"quotation_id": "s1", "supplier_name": "Supplier 1", "price": 100, "quality": 100},
            {"quotation_id": "s2", "supplier_name": "Candidate", "price": 200, "quality": 0},
        ]
    }
    # Quality has 90% weight, price has only 10% weight.
    cfg = ScoringConfigurationCreate(
        name="High Quality Weight",
        criteria=[
            CriterionConfig(
                criterion_id="c-price",
                name="Price",
                weight=Decimal("0.1000"),
                direction=CriterionDirection.LOWER_IS_BETTER,
                source_type="price",
                source_field="price",
            ),
            CriterionConfig(
                criterion_id="c-qual",
                name="Quality",
                weight=Decimal("0.9000"),
                direction=CriterionDirection.HIGHER_IS_BETTER,
                source_type="custom",
                source_field="quality",
            ),
        ],
    )
    result = scoring_service.compute_bisection_breakeven(
        snapshot_matrix_data=matrix,
        config=cfg,
        candidate_id="s2",
        target_rank=1,
    )
    assert result.feasible is False
    assert "Infeasible" in result.notes


def test_bisection_breakeven_infeasible_when_knockout_failed(
    scoring_service: ScoringService,
    sample_snapshot_matrix: dict,
    sample_scoring_config: ScoringConfigurationCreate,
):
    """
    Supplier D is ineligible due to knockout rule.
    Breakeven must immediately declare infeasible and return explicit failure.
    """
    result = scoring_service.compute_bisection_breakeven(
        snapshot_matrix_data=sample_snapshot_matrix,
        config=sample_scoring_config,
        candidate_id="supp-d",
        target_rank=1,
    )
    assert result.feasible is False
    assert "ineligible" in result.notes.lower()


# --------------------------------------------------------------------------
# 3. SENSITIVITY REDISTRIBUTION EDGE CASES
# --------------------------------------------------------------------------


def test_sensitivity_multiple_unlocked_proportional(
    scoring_service: ScoringService,
    sample_scoring_config: ScoringConfigurationCreate,
):
    """
    One criterion varied, multiple unlocked criteria scale proportionally.
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


def test_sensitivity_some_criteria_locked(
    scoring_service: ScoringService,
    sample_scoring_config: ScoringConfigurationCreate,
):
    """
    crit-lead-time is locked at 0.30. Swept crit-price becomes 0.60.
    Remaining pool = 1.00 - 0.60 - 0.30 = 0.10.
    crit-incoterms receives all of the remaining 0.10.
    """
    redistributed = scoring_service.redistribute_weights(
        base_criteria=sample_scoring_config.criteria,
        swept_cid="crit-price",
        new_weight=Decimal("0.6000"),
        locked_cids=["crit-lead-time"],
    )
    assert sum(c.weight for c in redistributed) == Decimal("1.0000")
    p_crit = next(c for c in redistributed if c.criterion_id == "crit-price")
    lt_crit = next(c for c in redistributed if c.criterion_id == "crit-lead-time")
    inco_crit = next(c for c in redistributed if c.criterion_id == "crit-incoterms")

    assert p_crit.weight == Decimal("0.6000")
    assert lt_crit.weight == Decimal("0.3000")
    assert inco_crit.weight == Decimal("0.1000")


def test_sensitivity_all_remaining_criteria_locked_rejected_when_impossible(
    scoring_service: ScoringService,
    sample_scoring_config: ScoringConfigurationCreate,
):
    """
    All other criteria are locked (0.30 + 0.20 = 0.50).
    Sweeping crit-price to 0.70 is impossible (0.70 + 0.50 != 1.0000).
    Must raise SensitivityConstraintError.
    """
    with pytest.raises(SensitivityConstraintError) as exc_info:
        scoring_service.redistribute_weights(
            base_criteria=sample_scoring_config.criteria,
            swept_cid="crit-price",
            new_weight=Decimal("0.7000"),
            locked_cids=["crit-lead-time", "crit-incoterms"],
        )
    assert "exceeds 1.0000" in str(exc_info.value) or "cannot satisfy" in str(exc_info.value)


def test_sensitivity_zero_baseline_unlocked_pool_rejected(scoring_service: ScoringService):
    """
    Under policy proportional_unlocked_v1:
    If all unlocked criteria have zero baseline weight, proportional redistribution cannot arbitrarily
    invent importance; it must raise SensitivityConstraintError.
    """
    criteria = [
        CriterionConfig(
            criterion_id="c1",
            name="C1",
            weight=Decimal("1.0000"),
            direction=CriterionDirection.LOWER_IS_BETTER,
            source_type="price",
            source_field="p",
        ),
        CriterionConfig(
            criterion_id="c2",
            name="C2",
            weight=Decimal("0.0000"),
            direction=CriterionDirection.LOWER_IS_BETTER,
            source_type="custom",
            source_field="q",
        ),
    ]
    with pytest.raises(SensitivityConstraintError) as exc_info:
        scoring_service.redistribute_weights(
            base_criteria=criteria,
            swept_cid="c1",
            new_weight=Decimal("0.5000"),
            locked_cids=[],
        )
    assert "proportional_unlocked_v1" in str(exc_info.value)


# --------------------------------------------------------------------------
# 4. ENGINE POLICY METADATA COMPLETENESS
# --------------------------------------------------------------------------


def test_engine_policy_metadata_completeness():
    """
    Verifies that ENGINE_POLICY_METADATA captures all calculation semantics required for historical reproducibility.
    """
    assert ENGINE_POLICY_METADATA["engine_version"] == "1.0.0"
    assert ENGINE_POLICY_METADATA["canonical_payload_schema"] == "scoring-run-v1"
    assert ENGINE_POLICY_METADATA["provenance_hash_algorithm"] == "sha256"
    assert ENGINE_POLICY_METADATA["normalization_policy"] == "min_max"
    assert ENGINE_POLICY_METADATA["zero_variance_policy"] == "assign_100_percent"
    assert ENGINE_POLICY_METADATA["ranking_policy"] == "standard_competitive_1224"
    assert ENGINE_POLICY_METADATA["knockout_precedence"] == "pre_normalization_exclusion"
    assert ENGINE_POLICY_METADATA["missing_value_policy"] == "block_scoring"
    assert ENGINE_POLICY_METADATA["precision_policy"] == "full_decimal_internal_ranking_4dp_presentation"
    assert ENGINE_POLICY_METADATA["redistribution_policy"] == "proportional_unlocked_v1"
