from __future__ import annotations

import datetime as dt
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from procureflow.services.normalization.currency import NormalizationStatus


class MatrixSupplierHeader(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    quotation_id: str
    supplier_name: str
    supplier_reference: str | None = None
    status: str
    extraction_version: str = "1.0"
    original_currency: str = "USD"
    rfq_coverage_pct: float = 0.0
    quoted_items_count: int = 0
    total_rfq_items: int = 0
    quoted_grand_total: float = 0.0
    normalized_line_item_subtotal: float = 0.0
    normalized_comparable_total: float | None = None
    has_unknown_commercial_components: bool = False
    payment_terms_original: str = "Not specified"
    payment_terms_normalized: str = "Not specified"
    payment_terms_code: str = "CUSTOM"
    overall_lead_time_original: str = "Not specified"
    overall_lead_time_normalized: str = "Not specified"
    overall_lead_time_days: int | None = None
    unresolved_count: int = 0
    warnings_count: int = 0
    warnings: list[str] = Field(default_factory=list)


class MatrixLineItemCell(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    is_quoted: bool = True
    line_item_id: str | None = None
    quoted_description: str | None = None
    quoted_quantity: float | None = None
    quoted_unit: str | None = None
    quoted_unit_price: float | None = None
    quoted_total_price: float | None = None
    calculated_total_price: float | None = None
    has_math_discrepancy: bool = False
    math_discrepancy_amount: float | None = None
    original_currency: str | None = None

    # Canonical UOM and Scaled Price
    canonical_quantity: float | None = None
    canonical_unit: str | None = None
    uom_conversion_factor: float | None = None
    uom_status: NormalizationStatus = NormalizationStatus.NORMALIZED
    uom_warning: str | None = None

    # Currency Normalization
    fx_rate_used: float | None = None
    fx_effective_date: str | None = None
    fx_provider_id: str | None = None
    fx_status: NormalizationStatus = NormalizationStatus.NORMALIZED
    fx_warning: str | None = None

    # Fully Normalized Output in RFQ Reference Currency and Canonical Unit
    normalized_unit_price: float | None = None
    normalized_extended_price: float | None = None

    # Lead Time
    line_lead_time_days: int | None = None
    line_lead_time_display: str | None = None
    line_lead_time_type: str | None = None

    # Status and Traceability
    overall_cell_status: NormalizationStatus = NormalizationStatus.NORMALIZED
    is_human_overridden: bool = False
    override_id: str | None = None
    override_reason: str | None = None
    warnings: list[str] = Field(default_factory=list)
    source_evidence: dict[str, Any] | None = None
    source_page: int | None = None


class MatrixRequiredRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rfq_line_item_id: str
    position: int
    description: str
    required_quantity: float
    required_unit: str
    supplier_cells: dict[str, MatrixLineItemCell] = Field(default_factory=dict)


class MatrixExtraItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    line_item_id: str
    quotation_id: str
    supplier_name: str
    description_raw: str
    quantity: float
    unit: str
    unit_price: float
    currency: str
    total_price: float
    lead_time_days: int | None = None
    source_page: int | None = None


class RFQFXRateSetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rfq_id: str
    version: int
    base_currency: str
    effective_date: dt.date
    provider_id: str
    is_synthetic: bool
    rates: dict[str, float]
    created_by: str
    created_at: dt.datetime
    is_current: bool


class RFQFXRateSetCreate(BaseModel):
    base_currency: str = "USD"
    effective_date: dt.date = Field(default_factory=dt.date.today)
    provider_id: str = "rfq_custom"
    is_synthetic: bool = False
    rates: dict[str, float]  # e.g. {"EUR": 1.085, "MAD": 0.100}


class NormalizationOverrideCreate(BaseModel):
    quotation_id: str
    line_item_id: str | None = None
    field_name: str  # "unit_price", "uom", "lead_time", "payment_terms", "conversion_factor"
    override_value: dict[
        str, Any
    ]  # e.g. {"conversion_factor": 24.0} or {"normalized_unit_price": 12.50}
    override_reason: str


class NormalizationOverrideRevert(BaseModel):
    revert_reason: str = "Reverted to deterministic calculation"


class NormalizationOverrideRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rfq_id: str
    quotation_id: str
    line_item_id: str | None = None
    field_name: str
    original_value: dict[str, Any]
    previous_normalized_value: dict[str, Any] | None = None
    override_value: dict[str, Any]
    override_reason: str
    actor_id: str
    created_at: dt.datetime
    is_active: bool
    reverted_at: dt.datetime | None = None
    reverted_by: str | None = None
    revert_reason: str | None = None


class ComparisonSnapshotCreate(BaseModel):
    title: str | None = None


class ComparisonSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rfq_id: str
    snapshot_version: int
    normalization_engine_version: str
    reference_currency: str
    fx_rate_set_id: str | None = None
    title: str | None = None
    matrix_data: dict[str, Any]
    created_by: str
    created_at: dt.datetime


class ComparisonMatrixResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rfq_id: str
    rfq_title: str
    reference_currency: str
    normalization_engine_version: str = "1.0.0"
    fx_rate_set: RFQFXRateSetRead | None = None
    suppliers: list[MatrixSupplierHeader] = Field(default_factory=list)
    required_line_items: list[MatrixRequiredRow] = Field(default_factory=list)
    extra_line_items: list[MatrixExtraItem] = Field(default_factory=list)
    active_overrides_count: int = 0
    snapshots_count: int = 0
    warnings_summary: list[str] = Field(default_factory=list)
    computed_at: dt.datetime = Field(default_factory=dt.datetime.utcnow)
