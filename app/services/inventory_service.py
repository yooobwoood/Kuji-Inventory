from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud import inventory as inventory_crud
from app.crud import user as user_crud
from app.models.grade import KujiGrade
from app.schemas.inventory import ChangeType, InventoryAdjust


class InventoryAdjustmentError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def adjust_inventory(db: Session, payload: InventoryAdjust) -> KujiGrade:
    user = user_crud.get_by_id(db, payload.user_id)
    if user is None or not user.is_active:
        raise InventoryAdjustmentError("존재하지 않거나 비활성 사용자입니다.", status_code=404)

    stmt = select(KujiGrade).where(KujiGrade.id == payload.grade_id).with_for_update()
    grade = db.execute(stmt).scalar_one_or_none()
    if grade is None:
        raise InventoryAdjustmentError("등급을 찾을 수 없습니다.", status_code=404)

    before = grade.current_stock

    if payload.change_type == ChangeType.IN:
        delta = payload.quantity
        after = before + delta
    elif payload.change_type == ChangeType.OUT:
        delta = -payload.quantity
        after = before + delta
        if after < 0:
            raise InventoryAdjustmentError("재고가 0 미만이 될 수 없습니다.", status_code=400)
    else:
        after = payload.quantity
        delta = after - before
        if after < 0:
            raise InventoryAdjustmentError("재고는 0 이상이어야 합니다.", status_code=400)

    grade.current_stock = after
    inventory_crud.create_log(
        db,
        product_id=grade.product_id,
        grade_id=grade.id,
        user_id=payload.user_id,
        change_type=payload.change_type.value,
        quantity_delta=delta,
        before_qty=before,
        after_qty=after,
        reason=payload.reason,
    )
    db.commit()
    db.refresh(grade)
    return grade
