from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class ProductOut(BaseModel):
    id: int
    source_product_id: str | None
    name: str
    brand: str | None
    showroom_price: Decimal
    displayed_discount: Decimal | None
    brand_price: Decimal | None
    real_discount: Decimal | None
    product_url: str | None
    is_interesting: bool
    first_seen_at: datetime
    last_checked_at: datetime
    ai_status: str | None = None

    model_config = {"from_attributes": True}


class ProductListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ProductOut]
