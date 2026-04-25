# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Agent Python qui scrape Showroomprivé, valide les prix via des LLM (Claude, GPT-4o, Gemini) avec recherche web, score les vraies remises, persiste en PostgreSQL et notifie Slack. Une API FastAPI + un frontend Next.js permettent de piloter les scans, contrôler le cron, et lancer des analyses IA par article.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # remplir les credentials
docker compose up -d db
alembic upgrade head
```

## Commandes courantes

```bash
# API backend
uvicorn src.api.main:app --reload

# Frontend
cd frontend && npm install && npm run dev

# Scan CLI unique (sans API)
python -m src.app --once

# Migrations
alembic upgrade head
alembic revision --autogenerate -m "description"

# Stack Docker complète
docker compose up --build
```

## Architecture

### Pipeline de scan (`src/app.py:run_scan()`)

1. `ShowroomScraper.run()` — Playwright se connecte, découvre les ventes (`/catalog/sale/<id>`), extrait les `.js-product-card`, déduplique par `source_product_id`
2. `BrandPriceValidator.find_brand_price()` — récupère le prix officiel via JSON-LD `offers.price` ou regex HTML (nécessite `brand_reference_url` non-None — **intégration à câbler**)
3. `compute_real_discount()` / `is_interesting_offer()` — fonctions pures dans `src/scoring.py`
4. Upsert en DB sur `products.source_product_id`
5. `SlackNotifier.notify_deal()` si `is_interesting = True`

### API FastAPI (`src/api/`)

| Router | Endpoints |
|---|---|
| `scan.py` | `POST /scan/run`, `GET /scan/status` |
| `cron.py` | `POST /cron/start`, `POST /cron/stop`, `GET /cron/status` |
| `products.py` | `GET /products`, `GET /products/top10` |
| `ai.py` | `POST /ai/research`, `GET /ai/results`, `GET /ai/results/{id}` |

- Le state du scan est un singleton thread-safe (`src/api/scan_state.py`)
- Le cron tourne via APScheduler (`src/api/scheduler.py`), un seul job `showroom_scan`
- `CRON_AUTOSTART=true` démarre le cron au boot via le lifespan FastAPI

### AI Research Worker (`src/ai/`)

- `orchestrator.py:research_product()` tente les providers dans l'ordre `AI_PROVIDER_ORDER`, passe au suivant en cas d'exception
- Interface commune : `BaseAIProvider.verify(prompt) → AIVerdict`
- `ClaudeProvider` : tool use + Tavily search (boucle agentic sur `stop_reason == "tool_use"`)
- `OpenAIProvider` : responses API + `web_search_preview` natif
- `GeminiProvider` : `google_search` grounding natif
- Chaque provider se désactive silencieusement si sa clé API est absente
- Les résultats sont persistés dans `ai_research_jobs` ; TTL `AI_RESULT_TTL_HOURS` évite les re-analyses

### Base de données

- `products` — produits scrapés, upsert sur `source_product_id`
- `ai_research_jobs` — jobs IA avec statut `pending/running/done/error`, FK cascade vers `products`
- Migrations gérées par Alembic (`alembic/versions/`)
- PostgreSQL sur le port **55432** (évite les conflits avec instances locales sur 5432)
- `expire_on_commit=False` sur la session factory

### Frontend Next.js (`frontend/`)

- App Router, Tailwind, TanStack Query v5, sonner (toasts)
- `lib/api.ts` : client axios typé vers tous les endpoints
- `lib/types.ts` : types TS miroirs des schémas Pydantic
- Pages : `/dashboard` (scan + cron), `/top10`, `/articles` (filtres URL), `/ai-results`
- Polling adaptatif : 2s pendant un scan, 3s si jobs IA actifs, 30s sinon

### Settings (`src/config.py`)

`Settings` est un dataclass frozen chargé une fois par appel à `load_settings()` depuis `.env`. Toutes les valeurs ont des défauts. Ajouter un champ = modifier le dataclass **et** `load_settings()`.

## Points d'intégration à implémenter

- **`brand_reference_url`** dans `ShowroomScraper._parse_product_cards()` : actuellement `None`, ce qui empêche toute validation de prix réelle.
- **Sélecteurs CSS** (`.js-product-card`, `.hit-prices .fw-bold`, sélecteurs de login) : à ajuster si le DOM change. Tester avec `PLAYWRIGHT_HEADLESS=false` et `SHOWROOM_MAX_SALES_PER_SCAN=1`.
- **`_extract_sale_brand()`** : lit le breadcrumb/h1, peut nécessiter un tuning.

## Contraintes scraping

- Respecter les CGU de Showroomprivé — ne pas contourner les CAPTCHAs.
- En cas de challenge anti-bot, stopper le run et traiter manuellement.
- Captures de debug sauvegardées dans `artifacts/` en cas d'échec login/sélecteur.
- Session Playwright persistée dans `playwright/.auth/state.json` (`PLAYWRIGHT_STORAGE_STATE_PATH`).
