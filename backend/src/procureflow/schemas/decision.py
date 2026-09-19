"""
Phase 6 — Pydantic schemas for Decision Narrative & Human Award Workflow.

Covers narrative generation requests/responses, structured claims with
grounding validation, award lifecycle events, and DecisionContext.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from procureflow.utils.actor import sanitize_actor_string as _sanitize_actor_string

# ---------------------------------------------------------------------------
# ENUMERATIONS
# ---------------------------------------------------------------------------


class NarrativeType(str, Enum):
    COMPARISON_SUMMARY = "comparison_summary"
    TRADEOFF_ANALYSIS = "tradeoff_analysis"
    SENSITIVITY_SUMMARY = "sensitivity_summary"
    DECISION_SUPPORT_MEMO = "decision_support_memo"
    DECISION_CONSIDERATIONS = "decision_considerations"


class NarrativeOrigin(str, Enum):
    AI_GENERATED = "ai_generated"
    AI_GENERATED_HUMAN_REVISED = "ai_generated_human_revised"
    HUMAN_AUTHORED = "human_authored"


class ClaimType(str, Enum):
    DETERMINISTIC_FACT = "deterministic_fact"
    INTERPRETATION = "interpretation"
    LIMITATION = "limitation"


class GroundingStatus(str, Enum):
    VERIFIED = "verified"
    UNSUPPORTED = "unsupported"
    UNVERIFIABLE = "unverifiable"


class AwardStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    REVOKED = "revoked"


class AwardEventType(str, Enum):
    DRAFT_CREATED = "draft_created"
    CONFIRMED = "confirmed"
    REVOKED = "revoked"


# ---------------------------------------------------------------------------
# STRUCTURED FACT REFERENCE — Machine-readable context references
# ---------------------------------------------------------------------------


class FactReference(BaseModel):
    """Machine-readable reference to an authoritative DecisionContext value."""

    reference_type: str  # "supplier_score", "criterion_contribution", "rank", "normalized_value"
    supplier_id: str | None = None
    criterion_id: str | None = None
    field_path: str  # JSON path within DecisionContext, e.g. "suppliers[0].total_score"
    authoritative_value: str  # The exact string value from DecisionContext
    display_value: str | None = None  # Human-formatted display value


# ---------------------------------------------------------------------------
# NARRATIVE SECTIONS — Structured LLM output (instructor-enforced)
# ---------------------------------------------------------------------------


class SupplierAnalysis(BaseModel):
    """Per-supplier analysis section with structured fact references."""

    supplier_id: str
    supplier_name: str
    rank: int | None = None
    total_score: str  # Exact authoritative value rendered server-side
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    score_context: str = ""  # Brief textual context about the score


class NarrativeSections(BaseModel):
    """
    Structured narrative output validated by instructor.
    Critical numeric values reference DecisionContext authoritatively.
    """

    executive_summary: str
    ranking_explanation: str
    per_supplier_analysis: list[SupplierAnalysis] = Field(default_factory=list)
    trade_offs: str = ""
    decision_considerations: str = ""
    risk_factors: list[str] = Field(default_factory=list)
    data_limitations: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# NARRATIVE CLAIM — Grounded claim representation
# ---------------------------------------------------------------------------


class NarrativeClaimSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    claim_index: int
    text: str
    claim_type: ClaimType
    grounding_status: GroundingStatus
    referenced_supplier_ids: list[str] = Field(default_factory=list)
    referenced_criterion_ids: list[str] = Field(default_factory=list)
    referenced_evidence_ids: list[str] = Field(default_factory=list)
    fact_references: list[dict[str, Any]] | dict[str, Any] | None = None
    grounding_notes: str | None = None


# ---------------------------------------------------------------------------
# NARRATIVE REVISION — Append-only human edit
# ---------------------------------------------------------------------------


class NarrativeRevisionCreate(BaseModel):
    revised_text: str = Field(..., min_length=1)
    revision_rationale: str | None = None


class NarrativeRevisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    narrative_generation_id: str
    revision_number: int
    revised_text: str
    revision_rationale: str | None = None
    revised_by: str
    revised_at: datetime

    @field_validator("revised_by", mode="before")
    @classmethod
    def sanitize_revised_by(cls, v: Any) -> str:
        return _sanitize_actor_string(v)



# ---------------------------------------------------------------------------
# NARRATIVE GENERATION — Request / Response
# ---------------------------------------------------------------------------


class NarrativeGenerationRequest(BaseModel):
    scoring_run_id: str
    narrative_type: NarrativeType = NarrativeType.COMPARISON_SUMMARY
    include_sensitivity: bool = False
    human_unverified_note: str | None = None  # Explicitly unverified, never documentary evidence


class NarrativeGenerationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rfq_id: str
    decision_context_id: str
    narrative_type: NarrativeType
    generation_number: int
    origin: NarrativeOrigin

    # LLM metadata
    provider: str
    model_identifier: str
    prompt_template_version: str
    prompt_template_hash: str
    rendered_prompt_hash: str
    response_schema_version: str
    generation_parameters: dict[str, Any]

    # Output
    raw_structured_output: dict[str, Any]
    output_hash: str
    grounding_validation_result: dict[str, Any]

    # Superseded tracking
    is_superseded: bool
    superseded_reason: str | None = None

    # Timestamps
    generated_at: datetime
    created_by: str

    @field_validator("created_by", mode="before")
    @classmethod
    def sanitize_created_by(cls, v: Any) -> str:
        return _sanitize_actor_string(v)

    # Derived — populated by service layer
    claims: list[NarrativeClaimSchema] = Field(default_factory=list)
    revisions: list[NarrativeRevisionResponse] = Field(default_factory=list)
    current_origin: NarrativeOrigin = NarrativeOrigin.AI_GENERATED


# ---------------------------------------------------------------------------
# DECISION CONTEXT — Response
# ---------------------------------------------------------------------------


class DecisionContextResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rfq_id: str
    scoring_run_id: str
    context_schema_version: str
    context_payload: dict[str, Any]
    context_hash: str
    includes_sensitivity: bool
    created_by: str
    created_at: datetime

    @field_validator("created_by", mode="before")
    @classmethod
    def sanitize_created_by(cls, v: Any) -> str:
        return _sanitize_actor_string(v)


# ---------------------------------------------------------------------------
# AWARD DECISION — Lifecycle schemas
# ---------------------------------------------------------------------------


class AwardDecisionCreate(BaseModel):
    scoring_run_id: str
    narrative_generation_id: str | None = None
    awarded_supplier_id: str
    award_justification: str = Field(..., min_length=1)
    # Mandatory when awarded supplier is not Rank #1
    non_rank1_rationale: str | None = None


class AwardConfirm(BaseModel):
    final_justification: str | None = None  # Can override draft justification


class AwardRevoke(BaseModel):
    revocation_reason: str = Field(..., min_length=1)


class AwardDecisionEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    award_decision_id: str
    event_type: AwardEventType
    event_number: int
    event_payload: dict[str, Any]
    actor_principal: str
    actor_display_name: str | None = None
    created_at: datetime

    @field_validator("actor_principal", mode="before")
    @classmethod
    def sanitize_principal(cls, v: Any) -> str:
        return _sanitize_actor_string(v)



class AwardDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rfq_id: str
    scoring_run_id: str
    narrative_generation_id: str | None = None
    awarded_supplier_id: str
    awarded_supplier_name: str
    awarded_supplier_rank: int | None = None
    non_rank1_rationale: str | None = None
    current_status: AwardStatus
    provenance_hash: str | None = None
    created_by: str
    created_at: datetime
    events: list[AwardDecisionEventResponse] = Field(default_factory=list)

    @field_validator("created_by", mode="before")
    @classmethod
    def sanitize_created_by(cls, v: Any) -> str:
        return _sanitize_actor_string(v)

    # Derived — service layer populates
    is_based_on_latest_run: bool = True
    latest_scoring_run_id: str | None = None
