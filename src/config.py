from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


def _bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(value: str | None, default: int) -> int:
    if value is None:
        return default
    return int(value)


def _float(value: str | None, default: float) -> float:
    if value is None:
        return default
    return float(value)


@dataclass(frozen=True)
class Settings:
    showroom_email: str
    showroom_password: str
    showroom_login_url: str
    showroom_catalog_url: str
    showroom_max_sales_per_scan: int
    showroom_max_pages_per_sale: int
    database_url: str
    slack_webhook_url: str
    slack_channel: str
    scan_interval_seconds: int
    min_real_discount_percent: float
    max_showroom_price_eur: float
    playwright_headless: bool
    playwright_storage_state_path: str
    request_timeout_seconds: int


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        showroom_email=os.getenv("SHOWROOM_EMAIL", ""),
        showroom_password=os.getenv("SHOWROOM_PASSWORD", ""),
        showroom_login_url=os.getenv("SHOWROOM_LOGIN_URL", "https://www.showroomprive.com/"),
        showroom_catalog_url=os.getenv("SHOWROOM_CATALOG_URL", "https://www.showroomprive.com/"),
        showroom_max_sales_per_scan=_int(os.getenv("SHOWROOM_MAX_SALES_PER_SCAN"), 3),
        showroom_max_pages_per_sale=_int(os.getenv("SHOWROOM_MAX_PAGES_PER_SALE"), 5),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://showroom:showroom@localhost:55432/showroom",
        ),
        slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL", ""),
        slack_channel=os.getenv("SLACK_CHANNEL", "#deals"),
        scan_interval_seconds=_int(os.getenv("SCAN_INTERVAL_SECONDS"), 3600),
        min_real_discount_percent=_float(os.getenv("MIN_REAL_DISCOUNT_PERCENT"), 40.0),
        max_showroom_price_eur=_float(os.getenv("MAX_SHOWROOM_PRICE_EUR"), 150.0),
        playwright_headless=_bool(os.getenv("PLAYWRIGHT_HEADLESS"), True),
        playwright_storage_state_path=os.getenv(
            "PLAYWRIGHT_STORAGE_STATE_PATH",
            "playwright/.auth/state.json",
        ),
        request_timeout_seconds=_int(os.getenv("REQUEST_TIMEOUT_SECONDS"), 15),
    )
