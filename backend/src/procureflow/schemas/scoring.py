from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class CriterionScoreRead(BaseModel):
    id: str
    criterion_id: str
    criterion_name: str
    raw_value: str | None = None
    normalised_value: Decimal
    weighted_contribution: Decimal

    class Config:
        from_attributes = True


class SupplierScoreRead(BaseModel):
    id: str
    quotation_id: str
    supplier_name: str
    total_score: Decimal
    rank: int
    is_eliminated: bool
    elimination_reason: str | None = None
    criterion_scores: list[CriterionScoreRead] = Field(default_factory=list)

    class Config:
        from_attributes = True


class AINarrativeRead(BaseModel):
    id: str
    model_used: str
    raw_text: str
    edited_text: str | None = None
    generated_at: datetime

    class Config:
        from_attributes = True


class ScoreResultRead(BaseModel):
    id: str
    rfq_id: str
    scoring_strategy: str
    computed_at: datetime
    currency_snapshot: dict[str, Any] | None = None
    supplier_scores: list[SupplierScoreRead] = Field(default_factory=list)
    narrative: AINarrativeRead | None = None

    class Config:
        from_attributes = True


class DecisionCreate(BaseModel):
    selected_quotation_ids: list[str] = Field(..., min_length=1)
    justification: str = Field(..., min_length=10)
    followed_ai_recommendation: bool = True
    is_partial_award: bool = False


class DecisionRead(BaseModel):
    id: str
    rfq_id: str
    score_result_id: str
    decided_at: datetime
    decided_by: str
    selected_quotation_ids: list[str]
    justification: str
    followed_ai_recommendation: bool
    is_partial_award: bool

    class Config:
        from_attributes = True
