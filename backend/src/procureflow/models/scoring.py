from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
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

    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    configuration: Mapped[ScoringConfiguration] = relationship(
        "ScoringConfiguration", back_populates="runs"
    )
