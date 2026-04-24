# Roadmap — Showroom Deals Agent v2

## Vision

Ajouter deux capabilities majeures au-dessus du pipeline existant :

1. **Top 10 par remise réelle** — sélectionner les meilleures affaires du scan courant
2. **Vérification IA approfondie** — interroger un ou plusieurs LLM (Claude, GPT-4o, Gemini…) pour confirmer que le prix est réellement en promotion (recherche web, historique de prix, avis consommateurs)
3. **Interface web** — dashboard pour piloter le tout sans ligne de commande

---

## Architecture cible

```
┌─────────────────────────────────────────────────────────┐
│                        Frontend                         │
│  Next.js (ou React + Vite)  ·  Tailwind                 │
│                                                         │
│  Dashboard │ Top 10 │ Articles │ Cron control │ AI jobs │
└─────────────────────┬───────────────────────────────────┘
                      │ REST / WebSocket
┌─────────────────────▼───────────────────────────────────┐
│                     API Backend                         │
│  FastAPI  ·  Python 3.11                                │
│                                                         │
│  /scan/run        POST  – déclenche un scan immédiat    │
│  /scan/status     GET   – état du scan en cours         │
│  /cron/start      POST  – démarre le job périodique     │
│  /cron/stop       POST  – stoppe le job périodique      │
│  /cron/status     GET   – état + prochain run           │
│  /products        GET   – liste paginée + filtres       │
│  /products/top10  GET   – top 10 par real_discount      │
│  /ai/research     POST  – déclenche l'analyse IA        │
│  /ai/results/{id} GET   – résultat d'une analyse IA     │
└──────────┬──────────────────────────┬───────────────────┘
           │                          │
┌──────────▼──────────┐   ┌──────────▼──────────────────┐
│   Scraper existant  │   │       AI Research Worker     │
│   src/app.py        │   │   src/ai/researcher.py       │
│   ShowroomScraper   │   │                              │
│   BrandPriceValid.  │   │  • Claude (Anthropic API)    │
│   scoring.py        │   │  • GPT-4o (OpenAI API)       │
└──────────┬──────────┘   │  • Gemini (Google AI)        │
           │              │  • Recherche web (Tavily /   │
┌──────────▼──────────┐   │    Brave Search API)         │
│     PostgreSQL      │   │  • Camelcamelcamel / Keepa   │
│     port 55432      │   │    (historique prix Amazon)  │
│                     │◄──┤                              │
│  tables:            │   │  résultat: verdict JSON      │
│  · products         │   │  { is_real_deal, confidence, │
│  · ai_research_jobs │   │    sources, summary }        │
└─────────────────────┘   └─────────────────────────────┘
```

---

## 1. Top 10 articles

### Logique de sélection

À chaque scan, après upsert des produits, calculer le classement :

```sql
SELECT * FROM products
WHERE real_discount IS NOT NULL
  AND is_interesting = TRUE
ORDER BY real_discount DESC
LIMIT 10;
```

- Exposé via `GET /products/top10`
- Rafraîchi automatiquement après chaque scan
- Le frontend affiche le classement en temps réel (polling ou WebSocket)

---

## 2. AI Research Worker

### Objectif

Confirmer ou infirmer qu'un article est réellement en promotion en croisant :

- Le prix actuel sur Showroomprivé
- Le prix historique (Amazon, Idealo, Google Shopping)
- Des avis et forums consommateurs
- Le prix officiel de la marque

### Prompt système (exemple)

```
Tu es un expert en analyse de prix e-commerce.
Pour le produit suivant :
  - Nom : {name}
  - Marque : {brand}
  - Prix Showroomprivé : {showroom_price} €
  - Remise affichée : {displayed_discount}%
  - Prix de référence détecté : {brand_price} €
  - URL produit : {product_url}

Effectue une recherche pour :
1. Confirmer le prix habituel de ce produit (historique 6 mois)
2. Comparer avec les prix actuels chez d'autres revendeurs
3. Déterminer si la remise est réelle ou si le prix de référence est gonflé

Réponds en JSON :
{
  "is_real_deal": true/false,
  "confidence": 0-100,
  "real_market_price": <float ou null>,
  "sources": ["url1", "url2"],
  "summary": "<explication courte>"
}
```

### Providers supportés

| Provider | Modèle cible | Recherche web native |
|---|---|---|
| Anthropic | claude-opus-4-7 | via tool use + Brave/Tavily |
| OpenAI | gpt-4o | via responses API + web_search |
| Google | gemini-2.0-flash | via grounding natif |

Le worker essaie les providers dans l'ordre de priorité configuré (`AI_PROVIDER_ORDER`). Si un provider échoue, il passe au suivant.

### Nouveau schéma DB

```sql
CREATE TABLE ai_research_jobs (
  id            SERIAL PRIMARY KEY,
  product_id    INT REFERENCES products(id) ON DELETE CASCADE,
  provider      TEXT NOT NULL,          -- "claude", "openai", "gemini"
  status        TEXT NOT NULL DEFAULT 'pending',  -- pending/running/done/error
  is_real_deal  BOOLEAN,
  confidence    SMALLINT,
  real_market_price NUMERIC(10,2),
  sources       JSONB,
  summary       TEXT,
  raw_response  TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  finished_at   TIMESTAMPTZ
);
```

---

## 3. Frontend

### Pages / vues

#### Dashboard principal
- Statut du cron (actif / inactif, prochain run dans Xmin)
- Boutons : **Lancer un scan**, **Démarrer cron**, **Stopper cron**
- Compteur de produits en DB, dernière mise à jour

#### Top 10
- Tableau des 10 meilleures remises réelles du dernier scan
- Colonnes : nom, marque, prix showroom, prix marque, remise réelle, statut IA
- Action par ligne : **Analyser avec IA** (lance un job pour cet article)
- Sélection multiple → **Analyser la sélection**

#### Articles
- Liste paginée de tous les produits en DB
- Filtres : marque, remise min, prix max, "intéressant seulement", statut IA
- Tri : date, remise, prix
- Action par ligne / sélection multiple : **Lancer analyse IA**

#### Résultats IA
- Historique des jobs IA (statut, provider, verdict, confiance)
- Détail : sources consultées, résumé, réponse brute

### Stack frontend suggérée

```
Next.js 14 (App Router)
Tailwind CSS + shadcn/ui
TanStack Query (polling des jobs IA)
Recharts (graphe historique prix si disponible)
```

---

## 4. Nouvelles variables d'environnement

```env
# Backend API
API_HOST=0.0.0.0
API_PORT=8000

# AI providers (laisser vide pour désactiver)
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GOOGLE_AI_API_KEY=

# Ordre de priorité des providers (comma-separated)
AI_PROVIDER_ORDER=claude,openai,gemini

# Recherche web pour Claude
TAVILY_API_KEY=
# ou
BRAVE_SEARCH_API_KEY=
```

---

## 5. Plan d'implémentation

### Étape 1 — Backend API (FastAPI)
- [ ] `src/api/main.py` — app FastAPI + CORS
- [ ] `src/api/routers/scan.py` — `/scan/run`, `/scan/status`
- [ ] `src/api/routers/cron.py` — `/cron/start`, `/cron/stop`, `/cron/status`
- [ ] `src/api/routers/products.py` — `/products`, `/products/top10`
- [ ] `src/api/routers/ai.py` — `/ai/research`, `/ai/results/{id}`
- [ ] Intégrer `APScheduler` (ou `rq`) pour le cron contrôlable via API

### Étape 2 — AI Research Worker
- [ ] `src/ai/researcher.py` — orchestrateur multi-provider
- [ ] `src/ai/providers/claude.py` — tool use + recherche web
- [ ] `src/ai/providers/openai.py` — responses API + web_search
- [ ] `src/ai/providers/gemini.py` — grounding Google
- [ ] Migration Alembic — table `ai_research_jobs`

### Étape 3 — Frontend
- [ ] Scaffold Next.js dans `frontend/`
- [ ] Page Dashboard + contrôle cron
- [ ] Page Top 10 + action "Analyser"
- [ ] Page Articles + filtres
- [ ] Page Résultats IA

### Étape 4 — Docker Compose
- [ ] Service `api` (FastAPI, port 8000)
- [ ] Service `frontend` (Next.js, port 3000)
- [ ] Mettre à jour le service `app` existant (scraper autonome ou intégré à l'API)

---

## 6. docker-compose cible

```yaml
services:
  db:
    # inchangé — port 55432

  api:
    build: .
    command: uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      db:
        condition: service_healthy

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - api
```
