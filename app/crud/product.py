from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import KujiProduct


def get_by_id(db: Session, product_id: int) -> KujiProduct | None:
    return db.get(KujiProduct, product_id)


def get_by_name(db: Session, name: str) -> KujiProduct | None:
    return db.execute(select(KujiProduct).where(KujiProduct.name == name)).scalar_one_or_none()


def list_products(db: Session, *, active_only: bool = True) -> list[KujiProduct]:
    stmt = select(KujiProduct).order_by(KujiProduct.id)
    if active_only:
        stmt = stmt.where(KujiProduct.is_active.is_(True))
    return list(db.execute(stmt).scalars().all())


def create(db: Session, *, name: str, description: str | None) -> KujiProduct:
    row = KujiProduct(name=name, description=description)
    db.add(row)
    db.flush()
    return row


def update(db: Session, row: KujiProduct, *, name: str | None, is_active: bool | None) -> KujiProduct:
    if name is not None:
        row.name = name
    if is_active is not None:
        row.is_active = is_active
    db.flush()
    return row
