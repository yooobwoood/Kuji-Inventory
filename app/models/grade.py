from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class KujiGrade(Base):
    __tablename__ = "kuji_grades"
    __table_args__ = (
        UniqueConstraint("product_id", "grade_code", name="uq_grade_per_product"),
        CheckConstraint("current_stock >= 0", name="ck_current_stock_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("kuji_products.id"), nullable=False)
    grade_code: Mapped[str] = mapped_column(String(20), nullable=False)
    grade_name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    initial_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    product = relationship("KujiProduct", back_populates="grades")
    inventory_logs = relationship("InventoryLog", back_populates="grade")

