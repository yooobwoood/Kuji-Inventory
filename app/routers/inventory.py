from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.crud import inventory as inventory_crud
from app.schemas.inventory import CurrentStockRow, InventoryAdjust, InventoryLogRead
from app.services.inventory_service import InventoryAdjustmentError, adjust_inventory

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.post("/adjust")
def adjust(body: InventoryAdjust, db: Session = Depends(get_db)):
    try:
        grade = adjust_inventory(db, body)
        return {"ok": True, "grade_id": grade.id, "current_stock": grade.current_stock}
    except InventoryAdjustmentError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/current", response_model=list[CurrentStockRow])
def get_current(db: Session = Depends(get_db)) -> list[CurrentStockRow]:
    rows = inventory_crud.list_current_stock(db)
    return [
        CurrentStockRow(
            product_id=p.id,
            product_name=p.name,
            grade_id=g.id,
            grade_code=g.grade_code,
            grade_name=g.grade_name,
            current_stock=g.current_stock,
        )
        for p, g in rows
    ]


@router.get("/logs", response_model=list[InventoryLogRead])
def get_logs(
    product_id: int | None = Query(None),
    grade_id: int | None = Query(None),
    from_dt: datetime | None = Query(None, alias="from"),
    to_dt: datetime | None = Query(None, alias="to"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[InventoryLogRead]:
    return inventory_crud.list_logs(
        db,
        product_id=product_id,
        grade_id=grade_id,
        from_dt=from_dt,
        to_dt=to_dt,
        limit=limit,
    )
