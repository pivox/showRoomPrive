from __future__ import annotations

import argparse
import time
from datetime import UTC, datetime

try:
    from sqlalchemy import select
    from sqlalchemy.exc import OperationalError
except ModuleNotFoundError as exc:
    if exc.name == "sqlalchemy":
        raise SystemExit(
            "Dépendance manquante: SQLAlchemy.\n"
            "Active l'environnement du projet puis installe les dépendances:\n"
            "source .venv/bin/activate && pip install -r requirements.txt"
        ) from exc
    raise

from src.brands.price_validator import BrandPriceValidator
from src.config import load_settings
from src.db import init_db, make_session_factory
from src.models import Product
from src.notifier.slack import SlackNotifier
from src.scoring import compute_real_discount, is_interesting_offer
from src.showroom.scraper import ShowroomScraper


def run_scan() -> None:
    settings = load_settings()
    try:
        init_db(settings.database_url)
    except OperationalError as exc:
        raise RuntimeError(
            "Connexion PostgreSQL impossible. Vérifie DATABASE_URL et l'instance ciblée. "
            "Si un Postgres local tourne déjà sur 5432, utilise un port dédié du conteneur "
            "(ex: postgresql+psycopg2://showroom:showroom@localhost:55432/showroom)."
        ) from exc

    scraper = ShowroomScraper(settings)
    validator = BrandPriceValidator(settings)
    notifier = SlackNotifier(settings)
    session_factory = make_session_factory(settings.database_url)

    scraped_products = scraper.run()
    print(f"[scan] produits récupérés: {len(scraped_products)}")

    with session_factory() as session:
        for sp in scraped_products:
            brand_price = validator.find_brand_price(sp.brand_reference_url)
            real_discount = compute_real_discount(sp.showroom_price, brand_price)
            interesting = is_interesting_offer(
                settings=settings,
                showroom_price=sp.showroom_price,
                real_discount=real_discount,
            )

            stmt = select(Product).where(Product.source_product_id == sp.source_product_id)
            db_product = session.execute(stmt).scalar_one_or_none()

            if db_product is None:
                db_product = Product(
                    source_product_id=sp.source_product_id,
                    name=sp.name,
                    brand=sp.brand,
                    showroom_price=sp.showroom_price,
                    displayed_discount=sp.displayed_discount,
                    brand_price=brand_price,
                    real_discount=real_discount,
                    product_url=sp.product_url,
                    is_interesting=interesting,
                    first_seen_at=datetime.now(UTC),
                    last_checked_at=datetime.now(UTC),
                )
                session.add(db_product)
            else:
                db_product.name = sp.name
                db_product.brand = sp.brand
                db_product.showroom_price = sp.showroom_price
                db_product.displayed_discount = sp.displayed_discount
                db_product.brand_price = brand_price
                db_product.real_discount = real_discount
                db_product.product_url = sp.product_url
                db_product.is_interesting = interesting
                db_product.last_checked_at = datetime.now(UTC)

            if interesting:
                notifier.notify_deal(
                    name=sp.name,
                    brand=sp.brand,
                    showroom_price=sp.showroom_price,
                    brand_price=brand_price,
                    real_discount=real_discount,
                    product_url=sp.product_url,
                )

        session.commit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Showroom deals agent")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Exécute un scan unique puis termine.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings()

    if args.once:
        run_scan()
        return

    while True:
        started = time.time()
        try:
            run_scan()
        except Exception as exc:
            print(f"[error] scan failed: {exc}")
        elapsed = time.time() - started
        sleep_for = max(0, settings.scan_interval_seconds - int(elapsed))
        print(f"[loop] prochain scan dans {sleep_for} sec")
        time.sleep(sleep_for)


if __name__ == "__main__":
    main()
