# TICKET-001 — Setup FastAPI + refactor structure projet

**Epic:** Backend API Foundation  
**Priorité:** P0 — bloquant pour tous les autres tickets  
**Complexité:** M  
**Dépendances:** aucune

---

## Contexte

Le projet est actuellement un script CLI (`python -m src.app`). Pour exposer les fonctionnalités via une API REST consommable par le frontend, on introduit FastAPI. Le scraper existant ne change pas — il devient un module appelé par l'API.

## Objectif

Mettre en place l'application FastAPI avec la structure de dossiers, la gestion CORS, les settings étendus et le point d'entrée serveur.

---

## Structure cible

```
src/
  api/
    __init__.py
    main.py          ← app FastAPI, CORS, inclusion des routers
    deps.py          ← dépendances injectables (session DB, settings)
    routers/
      __init__.py
      scan.py        ← TICKET-002
      cron.py        ← TICKET-003
      products.py    ← TICKET-004
      ai.py          ← TICKET-010
  app.py             ← inchangé (mode CLI conservé)
```

---

## Tâches

### 1. Dépendances

Ajouter dans `requirements.txt` :
```
fastapi==0.115.0
uvicorn[standard]==0.30.6
```

### 2. `src/api/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routers import scan, cron, products, ai

app = FastAPI(title="Showroom Deals Agent", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # surcharger via env CORS_ORIGINS
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scan.router,     prefix="/scan",     tags=["scan"])
app.include_router(cron.router,     prefix="/cron",     tags=["cron"])
app.include_router(products.router, prefix="/products", tags=["products"])
app.include_router(ai.router,       prefix="/ai",       tags=["ai"])

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
```

### 3. `src/api/deps.py`

Fournir deux dépendances injectables :

```python
from collections.abc import Generator
from sqlalchemy.orm import Session
from src.config import load_settings, Settings
from src.db import make_session_factory

def get_settings() -> Settings:
    return load_settings()

def get_db(settings: Settings = Depends(get_settings)) -> Generator[Session, None, None]:
    factory = make_session_factory(settings.database_url)
    with factory() as session:
        yield session
```

### 4. Nouvelles variables dans `src/config.py`

Ajouter dans le dataclass `Settings` et dans `load_settings()` :

```python
api_host: str           # API_HOST, défaut "0.0.0.0"
api_port: int           # API_PORT, défaut 8000
cors_origins: list[str] # CORS_ORIGINS, défaut ["http://localhost:3000"]
```

Parser `cors_origins` depuis une string CSV : `"http://localhost:3000,https://monapp.com"`.

### 5. Point d'entrée

Le projet doit pouvoir démarrer avec :
```bash
uvicorn src.api.main:app --reload
# ou
python -m src.api.main   # via if __name__ == "__main__": uvicorn.run(...)
```

Le mode CLI existant (`python -m src.app`) doit continuer à fonctionner sans modification.

---

## Acceptance criteria

- [ ] `GET /health` retourne `{"status": "ok"}` avec HTTP 200
- [ ] Les routes des autres tickets sont montées sans erreur (stubs 501 acceptés)
- [ ] `python -m src.app --once` continue de fonctionner
- [ ] CORS autorise `http://localhost:3000`
- [ ] Aucune régression sur les imports existants
