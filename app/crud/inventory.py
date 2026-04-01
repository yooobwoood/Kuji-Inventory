from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.grade import KujiGrade
from app.models.inventory_log import InventoryLog
from app.models.product import KujiProduct


def list_current_stock(db: Session) -> list[tuple[KujiProduct, KujiGrade]]:
    stmt = (
        select(KujiProduct, KujiGrade)
        .join(KujiGrade, KujiGrade.product_id == KujiProduct.id)
        .where(KujiProduct.is_active.is_(True))
        .order_by(KujiProduct.id, KujiGrade.sort_order, KujiGrade.id)
    )
    return list(db.execute(stmt).all())


def list_logs(
    db: Session,
    *,
    product_id: int | None = None,
    grade_id: int | None = None,
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
    limit: int = 200,
) -> list[InventoryLog]:
    stmt = select(InventoryLog).order_by(InventoryLog.created_at.desc())
    if product_id is not None:
        stmt = stmt.where(InventoryLog.product_id == product_id)
    if grade_id is not None:
        stmt = stmt.where(InventoryLog.grade_id == grade_id)
    if from_dt is not None:
        stmt = stmt.where(InventoryLog.created_at >= from_dt)
    if to_dt is not None:
        stmt = stmt.where(InventoryLog.created_at <= to_dt)
    stmt = stmt.limit(limit)
    return list(db.execute(stmt).scalars().all())


def create_log(
    db: Session,
    *,
    product_id: int,
    grade_id: int,
    user_id: int,
    change_type: str,
    quantity_delta: int,
    before_qty: int,
    after_qty: int,
    reason: str | None,
) -> InventoryLog:
    row = InventoryLog(
        product_id=product_id,
        grade_id=grade_id,
        user_id=user_id,
        change_type=change_type,
        quantity_delta=quantity_delta,
        before_qty=before_qty,
        after_qty=after_qty,
        reason=reason,
    )
    db.add(row)
    db.flush()
    return row
