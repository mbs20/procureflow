from __future__ import annotations

import datetime as dt
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from procureflow.database import Base


class RFQFXRateSet(Base):
    """
    Versioned, immutable set of FX rates configured for an RFQ.
    Preserves provenance and allows reproducible comparison snapshots.
    Reciprocal currency rates are deterministically derived from canonical rates against base_currency.
    """

    __tablename__ = "rfq_fx_rate_sets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rfq_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    effective_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    provider_id: Mapped[str] = mapped_column(String(100), default="rfq_custom", nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Dictionary mapping currency codes to multiplier against base_currency (e.g. {"EUR": 1.0850, "MAD": 0.1000})
    rates: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (Index("idx_fx_rateset_rfq_ver", "rfq_id", "version", unique=True),)


class NormalizationOverride(Base):
    """
    Append-only record of human reviewer overrides to normalized values (FX rate, UOM factor, lead time, etc.).
    Reverting an override updates is_active=False and records revert metadata rather than deleting the row.
    """

    __tablename__ = "normalization_overrides"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rfq_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False
    )
    quotation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("supplier_quotations.id", ondelete="CASCADE"), nullable=False
    )
    line_item_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("extracted_line_items.id", ondelete="CASCADE"), nullable=True
    )
    field_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # "unit_price", "uom", "lead_time", "payment_terms", "quantity"

    original_value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    previous_normalized_value: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    override_value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    override_reason: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[str] = mapped_column(String(100), default="human_reviewer", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Append-only revert management
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reverted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reverted_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    revert_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("idx_norm_override_rfq", "rfq_id", "is_active"),)


class ComparisonSnapshot(Base):
    """
    Immutable snapshot of a supplier comparison run for an RFQ.
    Guarantees that historical comparisons are 100% reproducible later.
    """

    __tablename__ = "comparison_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rfq_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rfqs.id", ondelete="CASCADE"), nullable=False
    )
    snapshot_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    normalization_engine_version: Mapped[str] = mapped_column(
        String(50), default="1.0.0", nullable=False
    )
    reference_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    fx_rate_set_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("rfq_fx_rate_sets.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    matrix_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        Index("idx_comparison_snapshot_rfq_ver", "rfq_id", "snapshot_version", unique=True),
    )
