from __future__ import annotations

import enum
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _utc_now() -> datetime:
    return datetime.now(UTC)


class AIJobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done = "done"
    error = "error"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_product_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    brand: Mapped[str | None] = mapped_column(String(255), nullable=True)
    showroom_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    displayed_discount: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    brand_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    real_discount: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    product_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    is_interesting: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    ai_jobs: Mapped[list[AIResearchJob]] = relationship(
        "AIResearchJob",
        back_populates="product",
        cascade="all, delete-orphan",
    )


class AIResearchJob(Base):
    __tablename__ = "ai_research_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[AIJobStatus] = mapped_column(
        SAEnum(AIJobStatus, name="aijobstatus"), nullable=False, default=AIJobStatus.pending
    )
    is_real_deal: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    confidence: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    real_market_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    sources: Mapped[list | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    product: Mapped[Product] = relationship("Product", back_populates="ai_jobs")
