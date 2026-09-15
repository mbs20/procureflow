"""
Phase 6 — Evidence-Backed Decision Narrative & Human Award Workflow

Domain models for immutable decision contexts, append-only narrative generations,
grounded claims, human revisions, event-sourced award decisions, and their lifecycle events.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from procureflow.database import Base


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
# DECISION CONTEXT — Immutable snapshot of Phase 1-5 data for narrative input
# ---------------------------------------------------------------------------


class DecisionContext(Base):
    """
    Immutable, versioned snapshot of all Phase 1–5 structured data required
    to generate an evidence-backed decision narrative.

    Preserves the exact canonical structured payload supplied to the narrative provider.
    Mutable RFQ fields are snapshotted at creation time.
    Sensitivity/breakeven results, when included, are frozen with their full
    input parameters and output values.
    """

    __tablename__ = "decision_contexts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    rfq_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scoring_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("scoring_runs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    context_schema_version: Mapped[str] = mapped_column(
        String(50), default="decision-context-v1", nullable=False
    )

    # Full canonical structured payload — the exact data the LLM saw
    context_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )
    context_hash: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # SHA-256 of canonical JSON payload

    # Privacy-minimized provider projection (sent to LLM)
    provider_projection: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )

    # Whether sensitivity/breakeven data is included
    includes_sensitivity: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    narrative_generations: Mapped[list[NarrativeGeneration]] = relationship(
        "NarrativeGeneration", back_populates="decision_context", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# NARRATIVE GENERATION — Immutable, append-only AI output
# ---------------------------------------------------------------------------


class NarrativeGeneration(Base):
    """
    Immutable record of a single narrative generation from an LLM or mock provider.
    Regeneration creates a new NarrativeGeneration (generation_number N+1);
    previous generations are never overwritten.
    """

    __tablename__ = "narrative_generations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    rfq_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    decision_context_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("decision_contexts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    narrative_type: Mapped[NarrativeType] = mapped_column(
        SQLEnum(NarrativeType), nullable=False
    )
    generation_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    origin: Mapped[NarrativeOrigin] = mapped_column(
        SQLEnum(NarrativeOrigin), default=NarrativeOrigin.AI_GENERATED, nullable=False
    )

    # LLM generation metadata
    provider: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "openai", "mock"
    model_identifier: Mapped[str] = mapped_column(
        String(200), nullable=False
    )  # e.g. "gpt-4o-mini"
    prompt_template_version: Mapped[str] = mapped_column(
        String(50), default="narrative-prompt-v1", nullable=False
    )
    prompt_template_hash: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # SHA-256 of prompt template text
    rendered_prompt_hash: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # SHA-256 of actual rendered prompt
    response_schema_version: Mapped[str] = mapped_column(
        String(50), default="narrative-sections-v1", nullable=False
    )
    generation_parameters: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )

    # Generated output
    raw_structured_output: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 of output

    # Grounding validation results
    grounding_validation_result: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )

    # Superseded tracking
    is_superseded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    superseded_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)

    # Relationships
    decision_context: Mapped[DecisionContext] = relationship(
        "DecisionContext", back_populates="narrative_generations"
    )
    claims: Mapped[list[NarrativeClaim]] = relationship(
        "NarrativeClaim", back_populates="narrative_generation", cascade="all, delete-orphan"
    )
    revisions: Mapped[list[NarrativeRevision]] = relationship(
        "NarrativeRevision", back_populates="narrative_generation", cascade="all, delete-orphan"
    )


# ---------------------------------------------------------------------------
# NARRATIVE CLAIM — Structured, grounded claim from an AI narrative
# ---------------------------------------------------------------------------


class NarrativeClaim(Base):
    """
    Individual grounded claim extracted from a NarrativeGeneration.
    Each claim references authoritative DecisionContext values
    through machine-readable fact references rather than free-text parsing.
    """

    __tablename__ = "narrative_claims"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    narrative_generation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("narrative_generations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claim_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[ClaimType] = mapped_column(SQLEnum(ClaimType), nullable=False)
    grounding_status: Mapped[GroundingStatus] = mapped_column(
        SQLEnum(GroundingStatus), nullable=False
    )

    # Machine-readable fact references
    referenced_supplier_ids: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    referenced_criterion_ids: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    referenced_evidence_ids: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )

    # Structured fact/value references to authoritative DecisionContext values
    fact_references: Mapped[list[dict[str, Any]] | dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )

    grounding_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship
    narrative_generation: Mapped[NarrativeGeneration] = relationship(
        "NarrativeGeneration", back_populates="claims"
    )


# ---------------------------------------------------------------------------
# NARRATIVE REVISION — Append-only human edits
# ---------------------------------------------------------------------------


class NarrativeRevision(Base):
    """
    Append-only record of a human edit to a NarrativeGeneration.
    The original AI generation is never overwritten.
    Multiple revisions create an append-only revision history.
    """

    __tablename__ = "narrative_revisions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    narrative_generation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("narrative_generations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    revised_text: Mapped[str] = mapped_column(Text, nullable=False)
    revision_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)

    revised_by: Mapped[str] = mapped_column(String(100), nullable=False)
    revised_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationship
    narrative_generation: Mapped[NarrativeGeneration] = relationship(
        "NarrativeGeneration", back_populates="revisions"
    )


# ---------------------------------------------------------------------------
# AWARD DECISION — Header record with event-sourced lifecycle
# ---------------------------------------------------------------------------


class AwardDecision(Base):
    """
    Award decision header record for an RFQ.
    The current state is derived from the latest AwardDecisionEvent.
    A transactionally-maintained current_status projection enables the database
    to enforce: at most one active confirmed award per RFQ.
    """

    __tablename__ = "award_decisions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    rfq_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scoring_run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("scoring_runs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    narrative_generation_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("narrative_generations.id", ondelete="SET NULL"),
        nullable=True,
    )
    awarded_supplier_id: Mapped[str] = mapped_column(String(36), nullable=False)
    awarded_supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    awarded_supplier_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Non-Rank-1 selection rationale (mandatory when rank != 1)
    non_rank1_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Operational state projection (updated transactionally with events)
    current_status: Mapped[AwardStatus] = mapped_column(
        SQLEnum(AwardStatus), default=AwardStatus.DRAFT, nullable=False
    )

    # Provenance hash (computed on confirmation, binding scoring + award data)
    provenance_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    events: Mapped[list[AwardDecisionEvent]] = relationship(
        "AwardDecisionEvent", back_populates="award_decision", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # Partial unique index: at most one confirmed award per RFQ at DB level
        Index(
            "uq_award_rfq_confirmed",
            "rfq_id",
            unique=True,
            postgresql_where=text("current_status = 'CONFIRMED'"),
            sqlite_where=text("current_status = 'CONFIRMED'"),
        ),
        Index("idx_award_rfq_status", "rfq_id", "current_status"),
    )


# ---------------------------------------------------------------------------
# AWARD DECISION EVENT — Append-only lifecycle events
# ---------------------------------------------------------------------------


class AwardDecisionEvent(Base):
    """
    Append-only event stream for AwardDecision lifecycle.
    Confirmation and revocation history remains fully reproducible.
    """

    __tablename__ = "award_decision_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    award_decision_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("award_decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[AwardEventType] = mapped_column(
        SQLEnum(AwardEventType), nullable=False
    )
    event_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Event payload (justification, rationale, reason, etc.)
    event_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )

    # Authenticated principal identity (derived from auth context, not request body)
    actor_principal: Mapped[str] = mapped_column(String(100), nullable=False)
    # Optional human-readable display name (distinct from authoritative principal)
    actor_display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationship
    award_decision: Mapped[AwardDecision] = relationship(
        "AwardDecision", back_populates="events"
    )
