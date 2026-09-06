from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from procureflow.models.extraction import ExtractedQuotation
    from procureflow.models.rfq import RFQ

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from procureflow.database import Base


class QuotationStatus(str, Enum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    EXTRACTING = "extracting"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"


class SupplierQuotation(Base):
    __tablename__ = "supplier_quotations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rfq_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False
    )
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    supplier_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[QuotationStatus] = mapped_column(
        SQLEnum(QuotationStatus), default=QuotationStatus.UPLOADED, nullable=False
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    rfq: Mapped[RFQ] = relationship("RFQ", back_populates="quotations")
    documents: Mapped[list[QuotationDocument]] = relationship(
        "QuotationDocument", back_populates="quotation", cascade="all, delete-orphan"
    )
    extractions: Mapped[list[ExtractedQuotation]] = relationship(
        "ExtractedQuotation", back_populates="quotation", cascade="all, delete-orphan"
    )


class QuotationDocument(Base):
    __tablename__ = "quotation_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quotation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("supplier_quotations.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    quotation: Mapped[SupplierQuotation] = relationship(
        "SupplierQuotation", back_populates="documents"
    )
