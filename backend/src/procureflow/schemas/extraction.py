from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class ExtractedLineItemBase(BaseModel):
    description_raw: str
    quantity: Decimal
    unit: str = "units"
    unit_price: Decimal
    currency: str = "USD"
    total_price: Decimal
    lead_time_days: int | None = None
    confidence: Decimal = Field(default=Decimal("1.0"), ge=0, le=1)
    source_page: int | None = None
    source_bbox: dict[str, Any] | None = None


class ExtractedLineItemUpdate(BaseModel):
    description_raw: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    unit_price: Decimal | None = None
    currency: str | None = None
    total_price: Decimal | None = None
    lead_time_days: int | None = None
    rfq_line_item_id: str | None = None


class ExtractedLineItemRead(ExtractedLineItemBase):
    id: str
    extracted_quotation_id: str
    rfq_line_item_id: str | None = None
    human_corrected: bool

    class Config:
        from_attributes = True


class ExtractedFieldRead(BaseModel):
    id: str
    field_name: str
    raw_value: str | None = None
    normalised_value: dict[str, Any] | None = None
    confidence: Decimal
    source_page: int | None = None
    source_bbox: dict[str, Any] | None = None
    human_corrected: bool

    class Config:
        from_attributes = True


class ExtractedQuotationRead(BaseModel):
    id: str
    quotation_id: str
    extraction_model: str
    extraction_version: str
    extracted_at: datetime
    overall_confidence: Decimal
    notes: str | None = None
    line_items: list[ExtractedLineItemRead] = Field(default_factory=list)
    fields: list[ExtractedFieldRead] = Field(default_factory=list)

    class Config:
        from_attributes = True
