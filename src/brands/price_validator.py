from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Any

import requests
from lxml import html

from src.config import Settings


class BrandPriceValidator:
    def __init__(self, settings: Settings):
        self.settings = settings

    def find_brand_price(self, reference_url: str | None) -> Decimal | None:
        if not reference_url:
            return None

        try:
            resp = requests.get(
                reference_url,
                timeout=self.settings.request_timeout_seconds,
                headers={"User-Agent": "Mozilla/5.0 (compatible; showroom-agent/1.0)"},
            )
            if resp.status_code != 200:
                return None
            return self._extract_price(resp.text)
        except requests.RequestException:
            return None

    def _extract_price(self, doc: str) -> Decimal | None:
        tree = html.fromstring(doc)

        # 1) JSON-LD (offers.price) - souvent la meilleure source.
        scripts = tree.xpath('//script[@type="application/ld+json"]/text()')
        for script in scripts:
            price = self._price_from_jsonld(script)
            if price is not None:
                return price

        # 2) Fallback regex sur le HTML.
        return self._price_from_text(doc)

    def _price_from_jsonld(self, raw: str) -> Decimal | None:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return None

        stack = payload if isinstance(payload, list) else [payload]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                offers = node.get("offers")
                if isinstance(offers, dict):
                    price_value = offers.get("price")
                    if price_value is not None:
                        return self._to_decimal(str(price_value))
                elif isinstance(offers, list):
                    stack.extend(offers)
                stack.extend(v for v in node.values() if isinstance(v, (dict, list)))
            elif isinstance(node, list):
                stack.extend(node)
        return None

    def _price_from_text(self, text: str) -> Decimal | None:
        match = re.search(r"([0-9]+(?:[.,][0-9]{1,2})?)\\s*€", text)
        if not match:
            return None
        return self._to_decimal(match.group(1))

    @staticmethod
    def _to_decimal(value: str) -> Decimal | None:
        cleaned = value.replace(",", ".").strip()
        try:
            return Decimal(cleaned)
        except Exception:
            return None

