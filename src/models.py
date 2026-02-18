from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _utc_now() -> datetime:
    return datetime.now(UTC)


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
