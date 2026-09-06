import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from procureflow.database import Base


class ScoreResult(Base):
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
    supplier_scores: Mapped[list["SupplierScore"]] = relationship(
        "SupplierScore",
        back_populates="score_result",
        cascade="all, delete-orphan",
        order_by="SupplierScore.rank",
    )
    narrative: Mapped[Optional["AINarrative"]] = relationship(
        "AINarrative", back_populates="score_result", uselist=False, cascade="all, delete-orphan"
    )


class SupplierScore(Base):
    __tablename__ = "supplier_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    score_result_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("score_results.id", ondelete="CASCADE"), nullable=False
    )
    quotation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("supplier_quotations.id", ondelete="CASCADE"), nullable=False
    )
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    total_score: Mapped[float] = mapped_column(Numeric(7, 4), nullable=False)  # e.g., 88.5000
    rank: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_eliminated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    elimination_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    score_result: Mapped["ScoreResult"] = relationship(
        "ScoreResult", back_populates="supplier_scores"
    )
    criterion_scores: Mapped[list["CriterionScore"]] = relationship(
        "CriterionScore", back_populates="supplier_score", cascade="all, delete-orphan"
    )


class CriterionScore(Base):
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
    normalised_value: Mapped[float] = mapped_column(Numeric(7, 4), nullable=False)  # 0.0 to 1.0
    weighted_contribution: Mapped[float] = mapped_column(Numeric(7, 4), nullable=False)

    supplier_score: Mapped["SupplierScore"] = relationship(
        "SupplierScore", back_populates="criterion_scores"
    )


class AINarrative(Base):
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

    score_result: Mapped["ScoreResult"] = relationship("ScoreResult", back_populates="narrative")


class ProcurementDecision(Base):
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
