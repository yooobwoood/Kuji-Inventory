from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class ChangeType(str, Enum):
    IN = "IN"
    OUT = "OUT"
    ADJUST = "ADJUST"


class InventoryAdjust(BaseModel):
    grade_id: int
    change_type: ChangeType
    quantity: int = Field(..., ge=0)
    reason: str | None = Field(None, max_length=255)
    user_id: int

    @model_validator(mode="after")
    def validate_quantity_by_type(self) -> "InventoryAdjust":
        if self.change_type in (ChangeType.IN, ChangeType.OUT) and self.quantity < 1:
            raise ValueError("IN/OUT일 때 quantity는 1 이상이어야 합니다.")
        return self


class CurrentStockRow(BaseModel):
    product_id: int
    product_name: str
    grade_id: int
    grade_code: str
    grade_name: str
    current_stock: int


class InventoryLogRead(BaseModel):
    id: int
    product_id: int
    grade_id: int
    user_id: int
    change_type: str
    quantity_delta: int
    before_qty: int
    after_qty: int
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
