# Showroom Deals Agent

Base de projet "prête à coder" pour:
- scanner un catalogue Showroomprive après login,
- détecter les nouveautés à intervalle régulier,
- valider le prix marque,
- scorer les remises réelles,
- notifier sur Slack.

## Important

- Respecte les CGU des sites ciblés.
- Ne contourne pas CAPTCHA / anti-bot.
- En cas de challenge, arrête le run et traite manuellement.

## Stack

- Python 3.11
- Playwright (navigation/login)
- PostgreSQL + SQLAlchemy
- Slack Incoming Webhook
- Docker Compose

## Arborescence

```text
src/
  app.py
  config.py
  db.py
  models.py
  scoring.py
  showroom/
    browser.py
    scraper.py
  brands/
    price_validator.py
  notifier/
    slack.py
sql/
  init.sql
```

## Démarrage local

1. Crée un environnement Python et installe les dépendances:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

2. Configure les variables:

```bash
cp .env.example .env
```

Par défaut, le projet expose Postgres sur `localhost:55432` pour éviter les conflits
avec des Postgres locaux/containers déjà actifs sur `5432/5433/5434`.

3. Lance PostgreSQL via Docker:

```bash
docker compose up -d db
```

4. Lance un scan unique:

```bash
python -m src.app --once
```

5. Lance en boucle (scan périodique):

```bash
python -m src.app
```

## Démarrage Docker complet

```bash
docker compose up --build
```

## Variables principales

- `SHOWROOM_EMAIL`, `SHOWROOM_PASSWORD`: credentials de connexion
- `SHOWROOM_LOGIN_URL`, `SHOWROOM_CATALOG_URL`: URLs à scraper
- `SHOWROOM_MAX_SALES_PER_SCAN`: nombre max de ventes scannées par run
- `SHOWROOM_MAX_PAGES_PER_SALE`: nombre max de pages scannées par vente
- `DATABASE_URL`: URL Postgres SQLAlchemy
- `SLACK_WEBHOOK_URL`: webhook Slack
- `SCAN_INTERVAL_SECONDS`: intervalle entre scans (défaut 3600)
- `MIN_REAL_DISCOUNT_PERCENT`: seuil de notification
- `MAX_SHOWROOM_PRICE_EUR`: plafond prix

## Flux listing Showroomprivé implémenté

- La home expose des liens de ventes (`/vente.aspx?vente=<id>`), pas les produits.
- Le scraper détecte ces ventes, les convertit en URLs `/catalog/sale/<id>`.
- Les produits sont récupérés depuis `.js-product-card` avec pagination `?page=N`.
- Les produits sont dédupliqués par `source_product_id`.
- Détails du flux: `docs/showroom_listing_flow.md`.

## État actuel

Ce bootstrap contient des squelettes robustes:
- login Playwright avec session persistée,
- extraction ventes/produits adaptée au DOM SSR actuel (`.js-product-card`),
- validation prix marque (JSON-LD + fallback regex),
- scoring + upsert DB + notification Slack.

Les sélecteurs Showroomprive et les règles métier doivent être ajustés sur tes pages réelles.

Note login Showroomprive: il n'y a pas toujours de page `/login` directe.
Le scraper ouvre la home, ferme la popin cookies, clique `Déjà membre ?` et remplit le popup de connexion.
