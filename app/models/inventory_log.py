from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InventoryLog(Base):
    __tablename__ = "inventory_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("kuji_products.id"), nullable=False)
    grade_id: Mapped[int] = mapped_column(ForeignKey("kuji_grades.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    change_type: Mapped[str] = mapped_column(String(10), nullable=False)  # IN, OUT, ADJUST
    quantity_delta: Mapped[int] = mapped_column(Integer, nullable=False)  # +증가, -감소
    before_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    after_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    product = relationship("KujiProduct", back_populates="inventory_logs")
    grade = relationship("KujiGrade", back_populates="inventory_logs")
    user = relationship("User", back_populates="inventory_logs")

