from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

from playwright.sync_api import Page

from src.config import Settings
from src.showroom.browser import context_with_persisted_state


@dataclass
class ScrapedProduct:
    source_product_id: str | None
    name: str
    brand: str | None
    showroom_price: Decimal
    displayed_discount: Decimal | None
    product_url: str | None
    brand_reference_url: str | None


class ShowroomScraper:
    def __init__(self, settings: Settings):
        self.settings = settings

    def run(self) -> Iterable[ScrapedProduct]:
        with context_with_persisted_state(
            headless=self.settings.playwright_headless,
            storage_state_path=self.settings.playwright_storage_state_path,
        ) as context:
            page = context.new_page()
            self._login_if_needed(page)
            return list(self._extract_products(page))

    def _login_if_needed(self, page: Page) -> None:
        if (
            not self.settings.showroom_email
            or not self.settings.showroom_password
            or self.settings.showroom_email == "you@example.com"
            or self.settings.showroom_password == "change-me"
        ):
            raise RuntimeError(
                "SHOWROOM_EMAIL / SHOWROOM_PASSWORD invalides dans .env. "
                "Renseigne tes vrais identifiants avant le login."
            )

        self._open_auth_entrypoint(page)
        self._dismiss_cookie_banner_if_present(page)

        if (
            not self._first_visible_selector(
                page,
                [
                    "#lLogin",
                    'input[name="login"]',
                    'input[type="email"]',
                    'input[autocomplete="username"]',
                    'input[placeholder*="Email"]',
                ],
            )
            and not self._appears_authenticated(page)
        ):
            self._open_member_login_modal(page)
            self._dismiss_cookie_banner_if_present(page)
            self._wait_for_login_form(page, timeout_ms=12000)

        email_selector, password_selector, submit_selector = self._resolve_login_selectors(page)

        if not email_selector or not password_selector or not submit_selector:
            # Retry once with an explicit modal open because the login UI is loaded lazily.
            self._open_member_login_modal(page)
            self._dismiss_cookie_banner_if_present(page)
            self._wait_for_login_form(page, timeout_ms=20000)
            email_selector, password_selector, submit_selector = self._resolve_login_selectors(page)

        if not email_selector or not password_selector or not submit_selector:
            if self._appears_authenticated(page):
                return
            if self._can_browse_without_auth(page):
                capture_path = self._save_debug_capture(page, "login_public_mode.png")
                print(
                    "[scraper] formulaire login introuvable, "
                    f"scan poursuivi en mode public (url={page.url}). "
                    f"Capture: {capture_path}"
                )
                return

            capture_path = self._save_debug_capture(page, "login_debug.png")
            raise RuntimeError(
                "Impossible de trouver les champs de login. "
                "Vérifie l'URL de login et adapte les sélecteurs dans src/showroom/scraper.py. "
                f"Capture enregistrée: {capture_path}"
            )

        page.fill(email_selector, self.settings.showroom_email)
        page.fill(password_selector, self.settings.showroom_password)
        page.click(submit_selector)
        try:
            page.wait_for_load_state("networkidle", timeout=12000)
        except Exception:
            page.wait_for_timeout(1500)

    @staticmethod
    def _wait_for_login_form(page: Page, timeout_ms: int = 12000) -> bool:
        selectors = [
            "#lLogin",
            "#lPassword",
            'input[name="login"]',
            'input[type="password"]',
            '.js-connexion_formulaire',
        ]
        for selector in selectors:
            try:
                page.wait_for_selector(selector, timeout=timeout_ms)
                return True
            except Exception:
                continue
        return False

    def _resolve_login_selectors(self, page: Page) -> tuple[str | None, str | None, str | None]:
        email_selector = self._first_existing_selector(
            page,
            [
                "#lLogin",
                'input[name="login"]',
                'input[type="email"]',
                'input[name="email"]',
                'input[id*="email"]',
                'input[autocomplete="username"]',
                'input[placeholder*="Email"]',
            ],
            visible_only=True,
        )
        password_selector = self._first_existing_selector(
            page,
            [
                "#lPassword",
                'input[name="password"]',
                'input[type="password"]',
                'input[id*="password"]',
                'input[autocomplete="current-password"]',
                'input[placeholder*="Mot de passe"]',
            ],
            visible_only=True,
        )
        submit_selector = self._first_existing_selector(
            page,
            [
                'button:has-text("Connexion")',
                'button[type="submit"]',
                'button:has-text("Se connecter")',
                'button:has-text("Log in")',
                '.js-connexion_formulaire button[type="submit"]',
            ],
            visible_only=True,
        )
        return email_selector, password_selector, submit_selector

    @staticmethod
    def _save_debug_capture(page: Page, filename: str) -> str:
        Path("artifacts").mkdir(parents=True, exist_ok=True)
        path = str(Path("artifacts") / filename)
        try:
            page.screenshot(path=path, full_page=True)
        except Exception:
            return "capture échouée"
        return path

    def _extract_products(self, page: Page) -> Iterable[ScrapedProduct]:
        self._open_catalog_entrypoint(page)
        sale_urls = self._discover_sale_catalog_urls(page)

        if not sale_urls:
            print("[scraper] aucune vente trouvée depuis la page d'entrée.")
            return []

        max_sales = max(1, self.settings.showroom_max_sales_per_scan)
        limited_sales = sale_urls[:max_sales]

        products_by_key: dict[str, ScrapedProduct] = {}
        for sale_url in limited_sales:
            sale_products = self._scrape_listing_url(
                page=page,
                listing_url=sale_url,
                max_pages=max(1, self.settings.showroom_max_pages_per_sale),
            )
            for sp in sale_products:
                key = self._product_dedupe_key(sp)
                products_by_key[key] = sp

        return list(products_by_key.values())

    def _open_catalog_entrypoint(self, page: Page) -> None:
        urls = []
        for candidate in [
            self.settings.showroom_catalog_url,
            self.settings.showroom_login_url,
            "https://www.showroomprive.com/",
        ]:
            if candidate and candidate not in urls:
                urls.append(candidate)

        for url in urls:
            page.goto(url, wait_until="domcontentloaded")
            self._dismiss_cookie_banner_if_present(page)
            if self._is_oops_page(page):
                continue
            return

        page.goto("https://www.showroomprive.com/", wait_until="domcontentloaded")
        self._dismiss_cookie_banner_if_present(page)

    def _discover_sale_catalog_urls(self, page: Page) -> list[str]:
        base_candidates: list[str] = []
        configured = self.settings.showroom_catalog_url.strip()
        if configured:
            normalized = self._normalized_listing_url(configured)
            if normalized:
                base_candidates.append(normalized)

        hrefs = page.eval_on_selector_all(
            "a[href]",
            "els => els.map(el => el.getAttribute('href')).filter(Boolean)",
        )

        sale_ids: list[str] = []
        for href in hrefs:
            sale_id = self._extract_sale_id_from_url(str(href))
            if sale_id:
                sale_ids.append(sale_id)

        for sale_id in self._unique_preserve_order(sale_ids):
            base_candidates.append(f"https://www.showroomprive.com/catalog/sale/{sale_id}")

        return self._unique_preserve_order(base_candidates)

    def _scrape_listing_url(
        self,
        page: Page,
        listing_url: str,
        max_pages: int,
    ) -> list[ScrapedProduct]:
        products: list[ScrapedProduct] = []

        first_page_url = self._with_page_param(listing_url, 1)
        page.goto(first_page_url, wait_until="domcontentloaded")
        self._dismiss_cookie_banner_if_present(page)

        if self._is_oops_page(page):
            print(f"[scraper] page indisponible: {first_page_url}")
            return products

        try:
            page.wait_for_selector(".js-product-card", timeout=8000)
        except Exception:
            pass

        detected_max_page = self._detect_max_page(page)
        pages_to_scan = min(max_pages, detected_max_page)
        sale_brand = self._extract_sale_brand(page)

        for page_num in range(1, pages_to_scan + 1):
            current_url = self._with_page_param(listing_url, page_num)
            if page_num > 1:
                page.goto(current_url, wait_until="domcontentloaded")
                self._dismiss_cookie_banner_if_present(page)
                try:
                    page.wait_for_selector(".js-product-card", timeout=8000)
                except Exception:
                    pass

            page_products = self._parse_product_cards(page, sale_brand)
            products.extend(page_products)
            print(
                f"[scraper] {current_url} -> {len(page_products)} produit(s)"
            )

        return products

    def _parse_product_cards(self, page: Page, sale_brand: str | None) -> list[ScrapedProduct]:
        cards = page.locator(".js-product-card")
        count = cards.count()
        if count == 0:
            return []

        products: list[ScrapedProduct] = []
        for idx in range(count):
            card = cards.nth(idx)

            source_product_id = self._extract_product_id_from_card(card)
            product_href = self._extract_product_href_from_card(card)
            product_url = urljoin(page.url, product_href) if product_href else None

            name = self._first_non_empty_text(
                card,
                [
                    "a.hit-product",
                    "a[href*='ficheproduitp.aspx?produit=']",
                    "img[alt]",
                ],
            )

            showroom_price = self._extract_price_from_card(card)
            if not name or showroom_price is None:
                continue

            displayed_discount = self._extract_discount_from_card(card)
            brand = sale_brand

            products.append(
                ScrapedProduct(
                    source_product_id=source_product_id,
                    name=name,
                    brand=brand,
                    showroom_price=showroom_price,
                    displayed_discount=displayed_discount,
                    product_url=product_url,
                    brand_reference_url=None,
                )
            )

        return products

    @staticmethod
    def _extract_price_from_card(card) -> Decimal | None:
        selectors = [
            ".hit-prices .fw-bold.txt-primary",
            ".hit-prices .fw-bold",
            ".hit-prices .txt-primary",
        ]

        for selector in selectors:
            locator = card.locator(selector)
            for i in range(locator.count()):
                text = (locator.nth(i).inner_text() or "").strip()
                if "€" not in text:
                    continue
                value = ShowroomScraper._to_decimal(text)
                if value is not None:
                    return value
        return None

    @staticmethod
    def _extract_discount_from_card(card) -> Decimal | None:
        selectors = [
            ".hit-prices .bg-neutral-200",
            ".hit-prices [class*='bg-neutral-200']",
            ".hit-prices .fw-bold",
        ]
        for selector in selectors:
            locator = card.locator(selector)
            for i in range(locator.count()):
                text = (locator.nth(i).inner_text() or "").strip()
                if "%" not in text:
                    continue
                parsed = ShowroomScraper._parse_percent(text)
                if parsed is not None:
                    return parsed
        return None

    def _extract_product_href_from_card(self, card) -> str | None:
        selectors = [
            "a.hit-product",
            "a[href*='ficheproduitp.aspx?produit=']",
            "a.js-image-swiper",
        ]
        for selector in selectors:
            locator = card.locator(selector)
            if locator.count() == 0:
                continue
            href = locator.first.get_attribute("href")
            if href:
                return href
        return None

    def _extract_product_id_from_card(self, card) -> str | None:
        direct_id = card.get_attribute("data-product-id")
        if direct_id:
            return direct_id

        for selector in ["[data-product-id]", "a[href*='produit=']", "button[data-product-id]"]:
            locator = card.locator(selector)
            if locator.count() == 0:
                continue
            if selector.startswith("["):
                found = locator.first.get_attribute("data-product-id")
                if found:
                    return found
            href = locator.first.get_attribute("href")
            if href:
                product_id = self._extract_product_id_from_url(href)
                if product_id:
                    return product_id

        return None

    @staticmethod
    def _extract_product_id_from_url(url: str) -> str | None:
        parsed = urlparse(url)
        produit = parse_qs(parsed.query).get("produit", [])
        if produit:
            return produit[0]
        match = re.search(r"produit=(\d+)", url)
        if match:
            return match.group(1)
        return None

    def _detect_max_page(self, page: Page) -> int:
        hrefs = page.eval_on_selector_all(
            "a[href*='page=']",
            "els => els.map(el => el.getAttribute('href')).filter(Boolean)",
        )

        pages = [1]
        for href in hrefs:
            parsed = urlparse(urljoin(page.url, str(href)))
            values = parse_qs(parsed.query).get("page", [])
            for value in values:
                if value.isdigit():
                    pages.append(int(value))

        return max(pages)

    def _extract_sale_brand(self, page: Page) -> str | None:
        selectors = [
            ".js-breadcrumb-title-wrapper:nth-child(2) a",
            "[id='sale-container'] .js-last-bc-el",
            "h1",
        ]
        for selector in selectors:
            locator = page.locator(selector)
            if locator.count() == 0:
                continue
            text = (locator.first.inner_text() or "").strip()
            if text and len(text) <= 255:
                return text
        return None

    @staticmethod
    def _with_page_param(listing_url: str, page_num: int) -> str:
        parsed = urlparse(listing_url)
        query = parse_qs(parsed.query)
        query["page"] = [str(page_num)]
        updated_query = urlencode(query, doseq=True)
        return urlunparse(parsed._replace(query=updated_query))

    @staticmethod
    def _extract_sale_id_from_url(url: str) -> str | None:
        parsed = urlparse(url)

        if parsed.path.startswith("/catalog/sale/"):
            match = re.search(r"/catalog/sale/(\d+)", parsed.path)
            if match:
                return match.group(1)

        vente_ids = parse_qs(parsed.query).get("vente", [])
        if vente_ids and vente_ids[0].isdigit():
            return vente_ids[0]

        match = re.search(r"vente=(\d+)", url)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _normalized_listing_url(url: str) -> str | None:
        parsed = urlparse(url)
        if "showroomprive.com" not in parsed.netloc and parsed.netloc:
            return None

        if parsed.path.startswith("/catalog/sale/"):
            if "/category/" in parsed.path:
                return url
            match = re.search(r"/catalog/sale/(\d+)", parsed.path)
            if match:
                return f"https://www.showroomprive.com/catalog/sale/{match.group(1)}"

        sale_id = ShowroomScraper._extract_sale_id_from_url(url)
        if sale_id:
            return f"https://www.showroomprive.com/catalog/sale/{sale_id}"

        if not parsed.netloc and parsed.path:
            absolute = urljoin("https://www.showroomprive.com/", parsed.path)
            return ShowroomScraper._normalized_listing_url(absolute)

        return None

    @staticmethod
    def _unique_preserve_order(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            result.append(value)
        return result

    @staticmethod
    def _product_dedupe_key(product: ScrapedProduct) -> str:
        if product.source_product_id:
            return f"id:{product.source_product_id}"
        if product.product_url:
            return f"url:{product.product_url}"
        return f"name:{product.name}:{product.showroom_price}"

    @staticmethod
    def _first_non_empty_text(root, selectors: list[str]) -> str:
        for selector in selectors:
            locator = root.locator(selector)
            if locator.count() == 0:
                continue
            text = (locator.first.inner_text() or "").strip()
            if text:
                return " ".join(text.split())

            alt_text = (locator.first.get_attribute("alt") or "").strip()
            if alt_text:
                return " ".join(alt_text.split())

        return ""

    @staticmethod
    def _to_decimal(value: str) -> Decimal | None:
        cleaned = value.replace("\u202f", " ")
        cleaned = cleaned.replace("€", " ").replace("%", " ")
        cleaned = cleaned.replace("\xa0", " ")
        cleaned = cleaned.replace(" ", "").replace(",", ".").strip()

        if not cleaned:
            return None

        match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
        if not match:
            return None

        return Decimal(match.group(0))

    @staticmethod
    def _parse_percent(value: str) -> Decimal | None:
        parsed = ShowroomScraper._to_decimal(value)
        if parsed is None:
            return None
        return abs(parsed)

    @staticmethod
    def _first_existing_selector(
        page: Page,
        selectors: list[str],
        visible_only: bool = False,
    ) -> str | None:
        for selector in selectors:
            locator = page.locator(selector)
            count = locator.count()
            if count == 0:
                continue
            if not visible_only:
                return selector
            for i in range(count):
                if locator.nth(i).is_visible():
                    return selector
        return None

    @staticmethod
    def _first_visible_selector(page: Page, selectors: list[str]) -> str | None:
        return ShowroomScraper._first_existing_selector(page, selectors, visible_only=True)

    def _dismiss_cookie_banner_if_present(self, page: Page) -> None:
        cookie_selectors = [
            "#agree_button",
            "#approveDetails",
            "#onetrust-accept-btn-handler",
            "#didomi-notice-agree-button",
            "#didomi-popup .didomi-continue-without-agreeing",
            "button[id*='didomi'][id*='agree']",
            "button[id*='accept']",
            "button:has-text(\"J'accepte\")",
            "button:has-text(\"J’accepte\")",
            "button:has-text(\"J'accepte tout\")",
            "button:has-text(\"J’accepte tout\")",
            "button:has-text(\"Tout accepter\")",
            "button:has-text(\"Tout Accepter\")",
            "button:has-text(\"Accepter\")",
            "button:has-text(\"Accepter tout\")",
            "button:has-text(\"Autoriser\")",
            "button:has-text(\"Autoriser tous\")",
            "button:has-text(\"I agree\")",
            "button:has-text(\"Accept\")",
            "button:has-text(\"Accept all\")",
            "button:has-text(\"Allow all\")",
            "[aria-label*='accepte' i]",
            "[aria-label*='accept' i]",
        ]

        for _ in range(6):
            clicked = False
            for root in [page, *page.frames]:
                if self._click_first_visible(root, cookie_selectors):
                    clicked = True
                    page.wait_for_timeout(500)
                    break
                if self._click_cookie_button_by_role(root):
                    clicked = True
                    page.wait_for_timeout(500)
                    break

            if clicked:
                return

            try:
                closed = page.evaluate(
                    """() => {
                        try {
                            if (window.SRP?.cookiesbanner?.agree) {
                                window.SRP.cookiesbanner.agree();
                                return true;
                            }
                            if (window.Didomi && typeof window.Didomi.setUserAgreeToAll === "function") {
                                window.Didomi.setUserAgreeToAll();
                                return true;
                            }
                        } catch (e) {}
                        return false;
                    }"""
                )
                if closed:
                    page.wait_for_timeout(500)
                    return
            except Exception:
                pass

            page.wait_for_timeout(350)

    @staticmethod
    def _click_cookie_button_by_role(root) -> bool:
        patterns = [
            r"j.?accepte",
            r"tout accepter",
            r"accepter",
            r"accept",
            r"allow",
            r"autoriser",
        ]

        for pattern in patterns:
            try:
                locator = root.get_by_role("button", name=re.compile(pattern, re.IGNORECASE))
                count = locator.count()
                if count == 0:
                    continue
                for i in range(count):
                    candidate = locator.nth(i)
                    if candidate.is_visible():
                        candidate.click(timeout=1500)
                        return True
            except Exception:
                continue

        return False

    def _open_member_login_modal(self, page: Page) -> None:
        self._dismiss_cookie_banner_if_present(page)
        page.wait_for_timeout(800)
        member_selectors = [
            "#loginBtn",
            "a#loginBtn",
            "#top-btn-member .js-btn-membre",
            ".js-btn-membre",
            'a:has-text("Déjà membre")',
            'text="Déjà membre"',
            'text="Déjà membre ?"',
        ]

        for selector in member_selectors:
            locator = page.locator(selector)
            if locator.count() == 0:
                continue
            for i in range(locator.count()):
                candidate = locator.nth(i)
                try:
                    if not candidate.is_visible():
                        continue
                    candidate.click(timeout=4000)
                    if self._wait_for_login_form(page, timeout_ms=12000):
                        return
                    self._dismiss_cookie_banner_if_present(page)
                except Exception:
                    self._dismiss_cookie_banner_if_present(page)

        page.evaluate(
            """() => {
                if (typeof window.openModalPublicOnboarding === "function") {
                    window.openModalPublicOnboarding(false);
                }
            }"""
        )
        self._wait_for_login_form(page, timeout_ms=12000)

    def _open_auth_entrypoint(self, page: Page) -> None:
        urls = []
        for candidate in [
            self.settings.showroom_login_url,
            self.settings.showroom_catalog_url,
            "https://www.showroomprive.com/",
        ]:
            if candidate and candidate not in urls:
                urls.append(candidate)

        for url in urls:
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(700)
            if self._is_oops_page(page):
                continue
            return

        page.goto("https://www.showroomprive.com/", wait_until="domcontentloaded")

    def _appears_authenticated(self, page: Page) -> bool:
        markers = [
            'a:has-text("Mon compte")',
            'a:has-text("Déconnexion")',
            "a[href*='deconnexion']",
            "a[href*='my-account']",
        ]
        for marker in markers:
            locator = page.locator(marker)
            if locator.count() == 0:
                continue
            for i in range(locator.count()):
                if locator.nth(i).is_visible():
                    return True

        member_buttons = page.locator("#loginBtn, .js-btn-membre")
        for i in range(member_buttons.count()):
            if member_buttons.nth(i).is_visible():
                return False

        return False

    @staticmethod
    def _can_browse_without_auth(page: Page) -> bool:
        selectors = [
            'a[href*="vente.aspx?vente="]',
            'a[href*="/catalog/sale/"]',
            ".js-btn-membre",
        ]
        for selector in selectors:
            locator = page.locator(selector)
            if locator.count() > 0:
                return True
        return False

    @staticmethod
    def _is_oops_page(page: Page) -> bool:
        title = (page.title() or "").lower()
        body_text = (page.locator("body").inner_text() or "").lower()
        return "oops" in title or "la page que vous cherchez" in body_text

    @staticmethod
    def _click_first_visible(root, selectors: list[str]) -> bool:
        for selector in selectors:
            try:
                locator = root.locator(selector)
                count = locator.count()
                if count == 0:
                    continue
                for i in range(count):
                    candidate = locator.nth(i)
                    if candidate.is_visible():
                        candidate.click(timeout=2000)
                        return True
            except Exception:
                continue
        return False
