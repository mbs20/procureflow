from datetime import datetime

from pydantic import BaseModel, Field

from procureflow.models.quotation import QuotationStatus


class DocumentRead(BaseModel):
    id: str
    quotation_id: str
    filename: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime

    class Config:
        from_attributes = True


class SupplierQuotationBase(BaseModel):
    supplier_name: str = Field(..., min_length=1, max_length=255)
    supplier_reference: str | None = Field(None, max_length=100)


class SupplierQuotationCreate(SupplierQuotationBase):
    rfq_id: str


class SupplierQuotationRead(SupplierQuotationBase):
    id: str
    rfq_id: str
    status: QuotationStatus
    failure_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    documents: list[DocumentRead] = Field(default_factory=list)

    class Config:
        from_attributes = True


class JobStatusResponse(BaseModel):
    quotation_id: str
    status: QuotationStatus
    failure_reason: str | None = None
    progress_percent: int = Field(default=0, ge=0, le=100)
    message: str | None = None


class QuotationStatusUpdate(BaseModel):
    status: QuotationStatus = Field(..., description="Target status (approved or rejected)")
    failure_reason: str | None = None
