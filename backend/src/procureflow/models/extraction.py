from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from procureflow.models.quotation import SupplierQuotation

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


class ExtractedQuotation(Base):
    __tablename__ = "extracted_quotations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quotation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("supplier_quotations.id", ondelete="CASCADE"), nullable=False
    )
    extraction_model: Mapped[str] = mapped_column(String(100), default="rule-based", nullable=False)
    extraction_version: Mapped[str] = mapped_column(String(50), default="1.0", nullable=False)
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    overall_confidence: Mapped[float] = mapped_column(Numeric(5, 4), default=1.0, nullable=False)
    raw_llm_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    quotation: Mapped[SupplierQuotation] = relationship(
        "SupplierQuotation", back_populates="extractions"
    )
    line_items: Mapped[list[ExtractedLineItem]] = relationship(
        "ExtractedLineItem", back_populates="extracted_quotation", cascade="all, delete-orphan"
    )
    fields: Mapped[list[ExtractedQuotationField]] = relationship(
        "ExtractedQuotationField",
        back_populates="extracted_quotation",
        cascade="all, delete-orphan",
    )


class ExtractedLineItem(Base):
    __tablename__ = "extracted_line_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    extracted_quotation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("extracted_quotations.id", ondelete="CASCADE"), nullable=False
    )
    rfq_line_item_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("rfq_line_items.id", ondelete="SET NULL"), nullable=True
    )
    description_raw: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), default="units", nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    total_price: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), default=1.0, nullable=False)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_bbox: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    human_corrected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    extracted_quotation: Mapped[ExtractedQuotation] = relationship(
        "ExtractedQuotation", back_populates="line_items"
    )


class ExtractedQuotationField(Base):
    __tablename__ = "extracted_quotation_fields"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    extracted_quotation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("extracted_quotations.id", ondelete="CASCADE"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g., payment_terms, validity_days
    raw_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalised_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), default=1.0, nullable=False)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_bbox: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    human_corrected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    extracted_quotation: Mapped[ExtractedQuotation] = relationship(
        "ExtractedQuotation", back_populates="fields"
    )
