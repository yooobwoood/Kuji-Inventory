from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_by_username(db: Session, username: str) -> User | None:
    return db.execute(select(User).where(User.username == username)).scalar_one_or_none()


def create(db: Session, *, username: str, password_hash: str, role: str = "admin") -> User:
    row = User(username=username, password_hash=password_hash, role=role)
    db.add(row)
    db.flush()
    return row


def list_active_users(db: Session) -> list[User]:
    return list(db.execute(select(User).where(User.is_active.is_(True)).order_by(User.id)).scalars().all())
