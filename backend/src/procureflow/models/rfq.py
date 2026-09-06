from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from procureflow.models.quotation import SupplierQuotation

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from procureflow.database import Base


class RFQStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    EVALUATING = "evaluating"
    DECIDED = "decided"
    ARCHIVED = "archived"


class CriterionDirection(str, Enum):
    LOWER_IS_BETTER = "lower_is_better"
    HIGHER_IS_BETTER = "higher_is_better"


class CriterionDataType(str, Enum):
    PRICE = "price"
    DAYS = "days"
    PERCENTAGE = "percentage"
    ENUM = "enum"
    BOOLEAN = "boolean"
    TEXT = "text"


class RFQ(Base):
    __tablename__ = "rfqs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), default="General", nullable=False)
    status: Mapped[RFQStatus] = mapped_column(
        SQLEnum(RFQStatus), default=RFQStatus.DRAFT, nullable=False
    )
    reference_currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    line_items: Mapped[list[RFQLineItem]] = relationship(
        "RFQLineItem",
        back_populates="rfq",
        cascade="all, delete-orphan",
        order_by="RFQLineItem.position",
    )
    criteria: Mapped[list[EvaluationCriterion]] = relationship(
        "EvaluationCriterion", back_populates="rfq", cascade="all, delete-orphan"
    )
    quotations: Mapped[list[SupplierQuotation]] = relationship(
        "SupplierQuotation", back_populates="rfq", cascade="all, delete-orphan"
    )


class RFQLineItem(Base):
    __tablename__ = "rfq_line_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rfq_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), default="units", nullable=False)

    rfq: Mapped[RFQ] = relationship("RFQ", back_populates="line_items")


class EvaluationCriterion(Base):
    __tablename__ = "evaluation_criteria"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rfq_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    weight: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)  # e.g., 0.4000
    direction: Mapped[CriterionDirection] = mapped_column(
        SQLEnum(CriterionDirection), default=CriterionDirection.LOWER_IS_BETTER, nullable=False
    )
    is_knockout: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    data_type: Mapped[CriterionDataType] = mapped_column(
        SQLEnum(CriterionDataType), default=CriterionDataType.PRICE, nullable=False
    )

    rfq: Mapped[RFQ] = relationship("RFQ", back_populates="criteria")
