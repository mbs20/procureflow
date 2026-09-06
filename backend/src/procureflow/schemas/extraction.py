from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ExtractedLineItemBase(BaseModel):
    description_raw: str
    quantity: Decimal
    unit: str = "units"
    unit_price: Decimal
    currency: str = "USD"
    total_price: Decimal  # Supplier quoted total
    calculated_total_price: Decimal | None = None  # ProcureFlow calculated (qty * unit_price)
    has_discrepancy: bool = False
    lead_time_days: int | None = None
    confidence: Decimal = Field(default=Decimal("1.0"), ge=0, le=1)
    source_page: int | None = None
    source_evidence: dict[str, Any] | None = None
    source_bbox: dict[str, Any] | None = None  # Deprecated alias for backward compatibility
    is_removed: bool = False
    removal_reason: str | None = None


class ExtractedLineItemCreate(BaseModel):
    description_raw: str
    quantity: Decimal
    unit: str = "units"
    unit_price: Decimal
    currency: str = "USD"
    total_price: Decimal | None = None
    lead_time_days: int | None = None
    rfq_line_item_id: str | None = None


class ExtractedLineItemUpdate(BaseModel):
    description_raw: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    unit_price: Decimal | None = None
    currency: str | None = None
    total_price: Decimal | None = None
    lead_time_days: int | None = None
    rfq_line_item_id: str | None = None
    is_removed: bool | None = None
    removal_reason: str | None = None


class ExtractedLineItemRead(ExtractedLineItemBase):
    id: str
    extracted_quotation_id: str
    rfq_line_item_id: str | None = None
    human_corrected: bool

    class Config:
        from_attributes = True

    @model_validator(mode="after")
    def sync_evidence_and_discrepancy(self) -> "ExtractedLineItemRead":
        if not self.source_evidence and self.source_bbox:
            self.source_evidence = self.source_bbox
        elif not self.source_bbox and self.source_evidence:
            self.source_bbox = self.source_evidence

        if self.calculated_total_price is not None and self.total_price is not None:
            self.has_discrepancy = abs(self.total_price - self.calculated_total_price) > Decimal(
                "0.01"
            )
        return self


class ExtractedFieldUpdate(BaseModel):
    raw_value: str | None = None
    normalised_value: dict[str, Any] | None = None


class ExtractedFieldRead(BaseModel):
    id: str
    field_name: str
    raw_value: str | None = None
    normalised_value: dict[str, Any] | None = None
    confidence: Decimal
    source_page: int | None = None
    source_evidence: dict[str, Any] | None = None
    source_bbox: dict[str, Any] | None = None  # Deprecated alias for backward compatibility
    human_corrected: bool

    class Config:
        from_attributes = True

    @model_validator(mode="after")
    def sync_field_evidence(self) -> "ExtractedFieldRead":
        if not self.source_evidence and self.source_bbox:
            self.source_evidence = self.source_bbox
        elif not self.source_bbox and self.source_evidence:
            self.source_bbox = self.source_evidence
        return self


class ExtractedQuotationRead(BaseModel):
    id: str
    quotation_id: str
    extraction_model: str
    extraction_version: str
    extracted_at: datetime
    overall_confidence: Decimal
    is_current: bool = True
    notes: str | None = None
    raw_llm_output: dict[str, Any] | None = None
    acknowledged_warnings: list[str] = Field(default_factory=list)
    line_items: list[ExtractedLineItemRead] = Field(default_factory=list)
    fields: list[ExtractedFieldRead] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ExtractionValidationStatus(BaseModel):
    can_approve: bool
    critical_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    acknowledged_warnings: list[str] = Field(default_factory=list)
