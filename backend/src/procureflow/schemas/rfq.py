from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from procureflow.models.rfq import CriterionDataType, CriterionDirection, RFQStatus


class LineItemBase(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    quantity: Decimal = Field(..., gt=0)
    unit: str = Field(default="units", max_length=50)


class LineItemCreate(LineItemBase):
    position: int | None = None


class LineItemRead(LineItemBase):
    id: str
    rfq_id: str
    position: int

    class Config:
        from_attributes = True


class CriterionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    weight: Decimal = Field(..., ge=0, le=1)
    direction: CriterionDirection = CriterionDirection.LOWER_IS_BETTER
    is_knockout: bool = False
    data_type: CriterionDataType = CriterionDataType.PRICE


class CriterionCreate(CriterionBase):
    pass


class CriterionRead(CriterionBase):
    id: str
    rfq_id: str

    class Config:
        from_attributes = True


class RFQBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    category: str = Field(default="General", max_length=100)
    reference_currency: str = Field(default="USD", min_length=3, max_length=3)


class RFQCreate(RFQBase):
    line_items: list[LineItemCreate] = Field(default_factory=list)
    criteria: list[CriterionCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_weights(self) -> "RFQCreate":
        if self.criteria:
            total_weight = sum(c.weight for c in self.criteria)
            if abs(total_weight - Decimal("1.0")) > Decimal("0.001"):
                raise ValueError(f"Criteria weights must sum to 1.0 (current sum: {total_weight})")
        return self


class RFQUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    category: str | None = None
    status: RFQStatus | None = None
    reference_currency: str | None = None
    is_archived: bool | None = None


class RFQRead(RFQBase):
    id: str
    status: RFQStatus
    created_by: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    line_items: list[LineItemRead] = Field(default_factory=list)
    criteria: list[CriterionRead] = Field(default_factory=list)

    class Config:
        from_attributes = True
