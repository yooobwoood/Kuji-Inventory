from collections import Counter

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


def process_draw_results(
    db: Session,
    *,
    product_id: int,
    user_id: int,
    quantity: int,
    result_codes: list[str],
) -> dict:
    user = user_crud.get_by_id(db, user_id)
    if user is None or not user.is_active:
        raise InventoryAdjustmentError("존재하지 않거나 비활성 사용자입니다.", status_code=404)
    if quantity < 1:
        raise InventoryAdjustmentError("수량은 1 이상이어야 합니다.", status_code=400)
    if len(result_codes) != quantity:
        raise InventoryAdjustmentError("수량과 입력한 결과 개수가 일치해야 합니다.", status_code=400)

    stmt = (
        select(KujiGrade)
        .where(KujiGrade.product_id == product_id)
        .with_for_update()
        .order_by(KujiGrade.id)
    )
    grades = list(db.execute(stmt).scalars().all())
    if not grades:
        raise InventoryAdjustmentError("해당 상품의 등급이 없습니다.", status_code=404)

    grade_by_code = {g.grade_code.upper(): g for g in grades}
    normalized_codes = [code.strip().upper() for code in result_codes if code.strip()]
    if len(normalized_codes) != quantity:
        raise InventoryAdjustmentError("빈 결과 코드가 포함되어 있습니다.", status_code=400)

    unknown_codes = sorted({code for code in normalized_codes if code not in grade_by_code})
    if unknown_codes:
        raise InventoryAdjustmentError(
            f"존재하지 않는 등급 코드가 있습니다: {', '.join(unknown_codes)}",
            status_code=400,
        )

    needed = Counter(normalized_codes)
    for code, count in needed.items():
        grade = grade_by_code[code]
        if grade.current_stock < count:
            raise InventoryAdjustmentError(
                f"{grade.grade_name} 재고가 부족합니다. 현재 {grade.current_stock}, 필요 {count}",
                status_code=400,
            )

    summary = ", ".join(f"{code} x{count}" for code, count in sorted(needed.items()))
    auto_reason = f"고객 뽑기 일괄 반영: {summary}"

    for code, count in needed.items():
        grade = grade_by_code[code]
        before = grade.current_stock
        after = before - count
        grade.current_stock = after
        inventory_crud.create_log(
            db,
            product_id=grade.product_id,
            grade_id=grade.id,
            user_id=user_id,
            change_type=ChangeType.OUT.value,
            quantity_delta=-count,
            before_qty=before,
            after_qty=after,
            reason=auto_reason,
        )

    db.commit()
    return {"product_id": product_id, "quantity": quantity, "applied": dict(needed)}
