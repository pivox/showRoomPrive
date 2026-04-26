"""create products table

Revision ID: 0001
Revises:
Create Date: 2026-04-25
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_product_id", sa.String(length=255), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("brand", sa.String(length=255), nullable=True),
        sa.Column("showroom_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("displayed_discount", sa.Numeric(6, 2), nullable=True),
        sa.Column("brand_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("real_discount", sa.Numeric(6, 2), nullable=True),
        sa.Column("product_url", sa.Text(), nullable=True),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "last_checked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "is_interesting",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_product_id"),
    )
    op.create_index("idx_products_last_checked_at", "products", ["last_checked_at"])
    op.create_index("idx_products_brand", "products", ["brand"])


def downgrade() -> None:
    op.drop_index("idx_products_brand", table_name="products")
    op.drop_index("idx_products_last_checked_at", table_name="products")
    op.drop_table("products")
