# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

A Python agent that logs into Showroomprivé, periodically scrapes flash-sale product listings, validates prices against brand reference pages, scores real discounts, persists results to PostgreSQL, and sends Slack alerts for interesting deals.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # then fill in credentials
```

Start the database:
```bash
docker compose up -d db
```

## Running

Single scan:
```bash
python -m src.app --once
```

Continuous loop (respects `SCAN_INTERVAL_SECONDS`):
```bash
python -m src.app
```

Full Docker stack (app + db):
```bash
docker compose up --build
```

## Architecture

The main pipeline in `src/app.py:run_scan()` wires together four components in sequence:

1. **`src/showroom/scraper.py` — `ShowroomScraper`**
   Uses Playwright (Chromium) to log in and scrape product listings. Browser session state is persisted to `playwright/.auth/state.json` (configured via `PLAYWRIGHT_STORAGE_STATE_PATH`) so subsequent runs reuse authenticated cookies. The login flow is resilient: it opens the home, dismisses the cookie banner, clicks "Déjà membre ?" to open the modal, and resolves the correct form selectors from a priority list. If no login form is found but the page has sale links, scraping continues in public mode. Sale IDs are extracted from `vente.aspx?vente=<id>` or `/catalog/sale/<id>` links; each sale is fetched at `/catalog/sale/<saleId>?page=N`. Product cards are parsed from `.js-product-card` elements and deduplicated by `source_product_id` (then URL, then name+price).

2. **`src/brands/price_validator.py` — `BrandPriceValidator`**
   Fetches each product's `brand_reference_url` (currently set to `None` in the scraper skeleton — this is the main integration point to wire up). Extracts the brand's official price from JSON-LD `offers.price` first, then falls back to a regex scan of the HTML. Uses plain `requests`, not Playwright.

3. **`src/scoring.py`**
   Pure functions: `compute_real_discount(showroom_price, brand_price)` computes the real percentage discount; `is_interesting_offer(settings, showroom_price, real_discount)` applies the `MIN_REAL_DISCOUNT_PERCENT` and `MAX_SHOWROOM_PRICE_EUR` thresholds.

4. **`src/notifier/slack.py` — `SlackNotifier`**
   Posts to a Slack Incoming Webhook. No-ops silently if `SLACK_WEBHOOK_URL` is empty.

**Database**: SQLAlchemy 2.x with `src/models.py` defining the single `products` table. `init_db()` runs `Base.metadata.create_all()` on startup (idempotent). Postgres runs on port **55432** (not 5432) to avoid conflicts with other local instances. Session factory is `expire_on_commit=False`.

**Settings**: All configuration is in `src/config.py` as a frozen `Settings` dataclass, loaded once per `run_scan()` call from environment variables / `.env` file via `python-dotenv`.

## Key integration points to implement

- **`brand_reference_url`** in `ShowroomScraper._parse_product_cards()`: currently hardcoded to `None`. Populate it from the product card (e.g. the brand's own site URL) to enable real discount validation.
- **CSS selectors** in `scraper.py`: the selectors (`.js-product-card`, `.hit-prices .fw-bold`, etc.) and the login selectors may need adjustment if Showroomprivé's DOM changes.
- **`_extract_sale_brand()`**: currently reads from breadcrumb/h1; may need tuning per actual page structure.

## Scraping constraints

Per README: respect Showroomprivé's ToS, do not attempt to bypass CAPTCHAs. If an anti-bot challenge is detected, stop the run and handle manually. Failed login/selector scenarios save a debug screenshot to `artifacts/`.
