from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from procureflow.database import Base


class ScoringConfiguration(Base):
    """
    Immutable versioned scoring configuration for an RFQ.
    Freezes criteria definitions, weights, directions, normalization method,
    categorical utility maps, knockout rules, missing-value policy, and tie policy.
    """

    __tablename__ = "scoring_configurations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rfq_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    engine_version: Mapped[str] = mapped_column(String(50), default="1.0", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Full configuration payload (criteria, weights, utility maps, knockout rules, policies)
    config_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )

    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    runs: Mapped[list[ScoringRun]] = relationship(
        "ScoringRun", back_populates="configuration", cascade="all, delete-orphan"
    )


class ScoringRun(Base):
    """
    Point-in-time calculation record binding exactly one ScoringConfiguration
    and one immutable ComparisonSnapshot. Historical runs are append-only and immutable.
    """

    __tablename__ = "scoring_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rfq_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    configuration_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("scoring_configurations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    snapshot_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("comparison_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    run_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Computed results payload (SupplierScore list, CriterionScoreBreakdowns, audit logs)
    results_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )
    provenance_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )  # SHA-256 integrity hash

    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    configuration: Mapped[ScoringConfiguration] = relationship(
        "ScoringConfiguration", back_populates="runs"
    )


class ScoreResult(Base):
    """
    Phase 0 legacy scoring model preserved for backwards compatibility and data preservation.
    """

    __tablename__ = "score_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rfq_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False
    )
    scoring_strategy: Mapped[str] = mapped_column(
        String(100), default="weighted_linear", nullable=False
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    currency_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    supplier_scores: Mapped[list[SupplierScore]] = relationship(
        "SupplierScore",
        back_populates="score_result",
        cascade="all, delete-orphan",
        order_by="SupplierScore.rank",
    )
    narrative: Mapped[AINarrative | None] = relationship(
        "AINarrative", back_populates="score_result", uselist=False, cascade="all, delete-orphan"
    )


class SupplierScore(Base):
    """
    Phase 0 legacy supplier score model preserved for backwards compatibility.
    """

    __tablename__ = "supplier_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    score_result_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("score_results.id", ondelete="CASCADE"), nullable=False
    )
    quotation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("supplier_quotations.id", ondelete="CASCADE"), nullable=False
    )
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    total_score: Mapped[float] = mapped_column(Numeric(7, 4), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_eliminated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    elimination_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    score_result: Mapped[ScoreResult] = relationship(
        "ScoreResult", back_populates="supplier_scores"
    )
    criterion_scores: Mapped[list[CriterionScore]] = relationship(
        "CriterionScore", back_populates="supplier_score", cascade="all, delete-orphan"
    )


class CriterionScore(Base):
    """
    Phase 0 legacy criterion score model preserved for backwards compatibility.
    """

    __tablename__ = "criterion_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    supplier_score_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("supplier_scores.id", ondelete="CASCADE"), nullable=False
    )
    criterion_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluation_criteria.id", ondelete="CASCADE"), nullable=False
    )
    criterion_name: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    normalised_value: Mapped[float] = mapped_column(Numeric(7, 4), nullable=False)
    weighted_contribution: Mapped[float] = mapped_column(Numeric(7, 4), nullable=False)

    supplier_score: Mapped[SupplierScore] = relationship(
        "SupplierScore", back_populates="criterion_scores"
    )


class AINarrative(Base):
    """
    Phase 0 legacy AI narrative model preserved for backwards compatibility.
    """

    __tablename__ = "ai_narratives"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    score_result_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("score_results.id", ondelete="CASCADE"), nullable=False
    )
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    edited_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    score_result: Mapped[ScoreResult] = relationship("ScoreResult", back_populates="narrative")


class ProcurementDecision(Base):
    """
    Phase 0 legacy procurement decision model preserved for backwards compatibility.
    """

    __tablename__ = "procurement_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rfq_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False
    )
    score_result_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("score_results.id", ondelete="RESTRICT"), nullable=False
    )
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    decided_by: Mapped[str] = mapped_column(
        String(100), default="procurement_officer", nullable=False
    )
    selected_quotation_ids: Mapped[list] = mapped_column(
        JSON, nullable=False
    )  # List of quotation UUID strings
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    followed_ai_recommendation: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_partial_award: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
