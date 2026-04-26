"""add ai_research_jobs table

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-25
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE aijobstatus AS ENUM ('pending', 'running', 'done', 'error')")

    op.create_table(
        "ai_research_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "done", "error", name="aijobstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("is_real_deal", sa.Boolean(), nullable=True),
        sa.Column("confidence", sa.SmallInteger(), nullable=True),
        sa.Column("real_market_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("sources", sa.JSON(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("raw_response", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_ai_jobs_product_id", "ai_research_jobs", ["product_id"])
    op.create_index(
        "idx_ai_jobs_product_status",
        "ai_research_jobs",
        ["product_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("idx_ai_jobs_product_status", table_name="ai_research_jobs")
    op.drop_index("idx_ai_jobs_product_id", table_name="ai_research_jobs")
    op.drop_table("ai_research_jobs")
    op.execute("DROP TYPE aijobstatus")
