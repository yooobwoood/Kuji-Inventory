from datetime import datetime

from pydantic import BaseModel, Field


class GradeCreate(BaseModel):
    grade_code: str = Field(..., min_length=1, max_length=20)
    grade_name: str = Field(..., min_length=1, max_length=100)
    sort_order: int = 0
    initial_stock: int = Field(0, ge=0)


class GradeUpdate(BaseModel):
    grade_name: str | None = Field(None, min_length=1, max_length=100)
    sort_order: int | None = None


class GradeRead(BaseModel):
    id: int
    product_id: int
    grade_code: str
    grade_name: str
    sort_order: int
    initial_stock: int
    current_stock: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
