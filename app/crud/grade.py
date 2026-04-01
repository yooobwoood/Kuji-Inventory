from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.grade import KujiGrade


def get_by_id(db: Session, grade_id: int) -> KujiGrade | None:
    return db.get(KujiGrade, grade_id)


def get_by_product_and_code(db: Session, product_id: int, grade_code: str) -> KujiGrade | None:
    return db.execute(
        select(KujiGrade).where(
            KujiGrade.product_id == product_id,
            KujiGrade.grade_code == grade_code,
        )
    ).scalar_one_or_none()


def list_by_product(db: Session, product_id: int) -> list[KujiGrade]:
    stmt = (
        select(KujiGrade)
        .where(KujiGrade.product_id == product_id)
        .order_by(KujiGrade.sort_order, KujiGrade.id)
    )
    return list(db.execute(stmt).scalars().all())


def create(
    db: Session,
    *,
    product_id: int,
    grade_code: str,
    grade_name: str,
    sort_order: int,
    initial_stock: int,
) -> KujiGrade:
    row = KujiGrade(
        product_id=product_id,
        grade_code=grade_code,
        grade_name=grade_name,
        sort_order=sort_order,
        initial_stock=initial_stock,
        current_stock=initial_stock,
    )
    db.add(row)
    db.flush()
    return row


def update(
    db: Session,
    row: KujiGrade,
    *,
    grade_name: str | None,
    sort_order: int | None,
) -> KujiGrade:
    if grade_name is not None:
        row.grade_name = grade_name
    if sort_order is not None:
        row.sort_order = sort_order
    db.flush()
    return row


def delete(db: Session, row: KujiGrade) -> None:
    db.delete(row)
    db.flush()
