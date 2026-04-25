# Showroom Deals Agent

Agent Python qui scrape Showroomprivé, valide les prix via des agents IA (Claude, GPT-4o, Gemini), score les vraies remises et notifie sur Slack.

## Stack

- Python 3.11 · FastAPI · Playwright · PostgreSQL · SQLAlchemy 2 · Alembic
- Next.js 14 · Tailwind · TanStack Query
- Anthropic / OpenAI / Google AI · Tavily Search
- Docker Compose

## Démarrage rapide

```bash
# 1. Environnement Python
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# 2. Configuration
cp .env.example .env   # remplir les credentials

# 3. Base de données
docker compose up -d db

# 4. Migrations
alembic upgrade head

# 5. API backend
uvicorn src.api.main:app --reload
# → http://localhost:8000

# 6. Frontend (autre terminal)
cd frontend && npm install && npm run dev
# → http://localhost:3000
```

### Stack complète Docker

```bash
docker compose up --build
```

## Variables d'environnement clés

| Variable | Description |
|---|---|
| `SHOWROOM_EMAIL` / `SHOWROOM_PASSWORD` | Credentials Showroomprivé |
| `DATABASE_URL` | PostgreSQL (défaut port 55432) |
| `SLACK_WEBHOOK_URL` | Webhook Slack (optionnel) |
| `ANTHROPIC_API_KEY` | Claude provider |
| `OPENAI_API_KEY` | GPT-4o provider |
| `GOOGLE_AI_API_KEY` | Gemini provider |
| `TAVILY_API_KEY` | Recherche web pour Claude |
| `AI_PROVIDER_ORDER` | Ordre de fallback (`claude,openai,gemini`) |
| `CRON_AUTOSTART` | Démarrer le cron au boot de l'API |
| `SCAN_INTERVAL_SECONDS` | Intervalle entre scans (défaut 3600) |

Voir `.env.example` pour la liste complète.

## Mode CLI (sans API)

```bash
# Scan unique
python -m src.app --once

# Boucle continue
python -m src.app
```

## Architecture

```
src/
  api/          FastAPI : routers scan, cron, products, ai
  ai/           Orchestrateur multi-provider + providers Claude/OpenAI/Gemini
  showroom/     Scraper Playwright (login + extraction ventes/produits)
  brands/       Validateur prix marque (JSON-LD + regex)
  scoring.py    Calcul remise réelle et seuil d'intérêt
  notifier/     Slack webhook
  models.py     SQLAlchemy : tables products + ai_research_jobs
  config.py     Settings dataclass chargé depuis .env
frontend/       Next.js 14 — Dashboard, Top 10, Articles, Résultats IA
```

## Contraintes scraping

- Respecter les CGU de Showroomprivé.
- Ne pas contourner les CAPTCHAs. En cas de challenge, stopper le run.
- Les captures de debug sont sauvegardées dans `artifacts/`.
