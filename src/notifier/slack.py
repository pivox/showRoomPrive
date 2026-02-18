from __future__ import annotations

from decimal import Decimal

import requests

from src.config import Settings


class SlackNotifier:
    def __init__(self, settings: Settings):
        self.settings = settings

    def notify_deal(
        self,
        name: str,
        brand: str | None,
        showroom_price: Decimal,
        brand_price: Decimal | None,
        real_discount: Decimal | None,
        product_url: str | None,
    ) -> None:
        if not self.settings.slack_webhook_url:
            return

        brand_part = f"*Marque:* {brand}\n" if brand else ""
        brand_price_part = f"*Prix marque:* {brand_price} EUR\n" if brand_price is not None else ""
        real_discount_part = (
            f"*Remise réelle:* {real_discount}%\n" if real_discount is not None else ""
        )
        url_part = f"*URL:* {product_url}\n" if product_url else ""

        text = (
            ":rotating_light: *Offre intéressante détectée*\n"
            f"*Produit:* {name}\n"
            f"{brand_part}"
            f"*Prix showroom:* {showroom_price} EUR\n"
            f"{brand_price_part}"
            f"{real_discount_part}"
            f"{url_part}"
        )

        payload = {"channel": self.settings.slack_channel, "text": text.strip()}
        requests.post(self.settings.slack_webhook_url, json=payload, timeout=10)

