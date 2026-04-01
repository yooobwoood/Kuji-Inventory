"""initial schema: users, products, grades, inventory_logs

Revision ID: 20260401_0001
Revises:
Create Date: 2026-04-01

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260401_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="admin"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "kuji_products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_kuji_products_id"), "kuji_products", ["id"], unique=False)
    op.create_index("ix_kuji_products_name", "kuji_products", ["name"], unique=True)

    op.create_table(
        "kuji_grades",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("grade_code", sa.String(length=20), nullable=False),
        sa.Column("grade_name", sa.String(length=100), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("initial_stock", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_stock", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("current_stock >= 0", name="ck_current_stock_non_negative"),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["kuji_products.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "grade_code", name="uq_grade_per_product"),
    )
    op.create_index(op.f("ix_kuji_grades_id"), "kuji_grades", ["id"], unique=False)

    op.create_table(
        "inventory_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("grade_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("change_type", sa.String(length=10), nullable=False),
        sa.Column("quantity_delta", sa.Integer(), nullable=False),
        sa.Column("before_qty", sa.Integer(), nullable=False),
        sa.Column("after_qty", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["grade_id"],
            ["kuji_grades.id"],
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["kuji_products.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inventory_logs_id"), "inventory_logs", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_inventory_logs_id"), table_name="inventory_logs")
    op.drop_table("inventory_logs")
    op.drop_index(op.f("ix_kuji_grades_id"), table_name="kuji_grades")
    op.drop_table("kuji_grades")
    op.drop_index("ix_kuji_products_name", table_name="kuji_products")
    op.drop_index(op.f("ix_kuji_products_id"), table_name="kuji_products")
    op.drop_table("kuji_products")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
