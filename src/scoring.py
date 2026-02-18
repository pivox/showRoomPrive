from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from src.config import Settings


def compute_real_discount(showroom_price: Decimal, brand_price: Decimal | None) -> Decimal | None:
    if brand_price is None or brand_price <= 0:
        return None
    discount = (brand_price - showroom_price) / brand_price * Decimal("100")
    return discount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def is_interesting_offer(
    settings: Settings,
    showroom_price: Decimal,
    real_discount: Decimal | None,
) -> bool:
    if showroom_price > Decimal(str(settings.max_showroom_price_eur)):
        return False
    if real_discount is None:
        return False
    return real_discount >= Decimal(str(settings.min_real_discount_percent))

