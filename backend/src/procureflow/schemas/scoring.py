from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CriterionDirection(str, Enum):
    LOWER_IS_BETTER = "lower_is_better"
    HIGHER_IS_BETTER = "higher_is_better"


class NormalizationMethod(str, Enum):
    MIN_MAX = "min_max"


class MissingValuePolicy(str, Enum):
    BLOCK_SCORING = "block_scoring"


class EligibilityStatus(str, Enum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    KNOCKOUT_FAILED = "knockout_failed"
    MISSING_VALUE_BLOCKED = "missing_value_blocked"


class TiePolicy(str, Enum):
    STANDARD_COMPETITIVE = "standard_competitive"  # e.g. 1, 2, 2, 4


class CriterionConfig(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    criterion_id: str
    name: str
    weight: Decimal = Field(..., ge=0, le=1)
    direction: CriterionDirection = CriterionDirection.LOWER_IS_BETTER
    source_type: str = "price"  # price, lead_time, payment_terms, incoterms, custom
    source_field: str = "normalized_comparable_total"
    is_knockout: bool = False
    knockout_threshold: Decimal | None = None
    # Categorical utility mapping must be explicitly configured by the evaluator (no universal defaults)
    categorical_map: dict[str, Decimal] | None = None


class ScoringConfigurationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    criteria: list[CriterionConfig]
    normalization_method: NormalizationMethod = NormalizationMethod.MIN_MAX
    missing_value_policy: MissingValuePolicy = MissingValuePolicy.BLOCK_SCORING
    tie_policy: TiePolicy = TiePolicy.STANDARD_COMPETITIVE
    engine_version: str = "1.0"

    @model_validator(mode="after")
    def validate_weights_sum(self) -> ScoringConfigurationCreate:
        if not self.criteria:
            raise ValueError("At least one criterion must be defined.")
        total_weight = sum(c.weight for c in self.criteria)
        # Check sum equals 1.0000 within 0.0001
        diff = abs(total_weight - Decimal("1.0000"))
        if diff > Decimal("0.0001"):
            raise ValueError(
                f"Criteria weights must sum exactly to 1.0000. Current sum is {total_weight}."
            )
        return self


class ScoringConfigurationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rfq_id: str
    version: int
    name: str
    description: str | None = None
    engine_version: str
    is_active: bool
    config_payload: dict[str, Any]
    created_by: str
    created_at: datetime


class CriterionScoreBreakdown(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    criterion_id: str
    criterion_name: str
    raw_value: Any
    source_path: str
    direction: CriterionDirection
    min_value: Decimal | None = None
    max_value: Decimal | None = None
    normalized_score: Decimal  # 0.00 to 100.00
    weight: Decimal
    weighted_contribution: Decimal  # normalized_score * weight
    formula_audit: str
    is_knockout_applied: bool = False
    notes: str | None = None


class SupplierScore(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    quotation_id: str
    supplier_name: str
    eligibility_status: EligibilityStatus
    knockout_reasons: list[str] = Field(default_factory=list)
    total_score: Decimal = Decimal("0.00")
    rank: int | None = None  # None if knockout_failed / blocked
    criteria_breakdown: list[CriterionScoreBreakdown] = Field(default_factory=list)


class ScoringRunCreate(BaseModel):
    snapshot_id: str
    configuration_id: str | None = None
    name: str = Field(..., min_length=1, max_length=255)
    notes: str | None = None


class ScoringRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rfq_id: str
    configuration_id: str
    snapshot_id: str
    run_number: int
    name: str
    notes: str | None = None
    results_payload: dict[str, Any]
    created_by: str
    created_at: datetime


class ScoringSimulationRequest(BaseModel):
    snapshot_id: str
    configuration_id: str | None = None
    custom_configuration: ScoringConfigurationCreate | None = None


class SensitivityRequest(BaseModel):
    snapshot_id: str
    configuration_id: str | None = None
    swept_criterion_id: str
    locked_criterion_ids: list[str] = Field(default_factory=list)
    step_size: Decimal = Field(default=Decimal("0.05"), gt=0, le=Decimal("0.50"))
    include_breakeven: bool = False
    breakeven_candidate_id: str | None = None


class SensitivityPoint(BaseModel):
    weight: Decimal
    redistributed_weights: dict[str, Decimal]
    supplier_scores: dict[str, Decimal]
    rankings: dict[str, int | None]


class CrossoverPoint(BaseModel):
    weight: Decimal
    supplier_a: str
    supplier_b: str
    score_at_crossover: Decimal


class BreakevenResult(BaseModel):
    candidate_id: str
    candidate_name: str
    target_rank: int = 1
    current_price: Decimal
    required_price: Decimal | None = None
    delta_price: Decimal | None = None
    delta_pct: Decimal | None = None
    feasible: bool
    convergence_steps: int
    evaluated_scores: dict[str, Decimal]
    notes: str


class SensitivityResponse(BaseModel):
    swept_criterion_id: str
    weight_redistribution_rule: str
    points: list[SensitivityPoint]
    crossover_points: list[CrossoverPoint]
    breakeven: BreakevenResult | None = None
