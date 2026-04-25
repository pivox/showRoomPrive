# TICKET-003 — Router /cron (scheduler contrôlable)

**Epic:** Backend API Foundation  
**Priorité:** P1  
**Complexité:** M  
**Dépendances:** TICKET-001, TICKET-002

---

## Contexte

Le mode boucle de `src/app.py` (`while True: run_scan(); sleep(N)`) n'est plus adapté quand l'API tourne en parallèle. On remplace ce mécanisme par APScheduler, piloté via des endpoints REST pour permettre au frontend de démarrer/stopper le cron sans redémarrer le serveur.

---

## Endpoints

### `POST /cron/start`

Démarre le job périodique. Sans effet si déjà actif.

**Réponse 200 :**
```json
{
  "status": "started",
  "interval_seconds": 3600,
  "next_run_at": "2026-04-25T11:00:00Z"
}
```

---

### `POST /cron/stop`

Stoppe le job périodique. Sans effet si déjà stoppé.

**Réponse 200 :**
```json
{ "status": "stopped" }
```

---

### `GET /cron/status`

**Réponse 200 :**
```json
{
  "active": true,
  "interval_seconds": 3600,
  "next_run_at": "2026-04-25T11:00:00Z",   // null si stoppé
  "last_run_at": "2026-04-25T10:00:00Z"    // null si jamais exécuté
}
```

---

## Implémentation

### Dépendance

Ajouter dans `requirements.txt` :
```
APScheduler==3.10.4
```

### Scheduler singleton

```python
# src/api/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

_scheduler = BackgroundScheduler(timezone="UTC")
_scheduler.start()   # démarré au lancement de l'API, aucun job actif initialement

JOB_ID = "showroom_scan"

def get_scheduler() -> BackgroundScheduler:
    return _scheduler
```

### Router

```python
# src/api/routers/cron.py
from datetime import datetime, UTC
from fastapi import APIRouter, Depends
from src.api.scheduler import get_scheduler, JOB_ID
from src.api.deps import get_settings
from src.app import run_scan
from apscheduler.triggers.interval import IntervalTrigger

router = APIRouter()

@router.post("/start")
def start(settings=Depends(get_settings)):
    scheduler = get_scheduler()
    job = scheduler.get_job(JOB_ID)

    if job is None:
        scheduler.add_job(
            run_scan,
            trigger=IntervalTrigger(seconds=settings.scan_interval_seconds),
            id=JOB_ID,
            replace_existing=True,
            next_run_time=datetime.now(UTC),   # premier run immédiat
        )
        job = scheduler.get_job(JOB_ID)

    return {
        "status": "started",
        "interval_seconds": settings.scan_interval_seconds,
        "next_run_at": job.next_run_time,
    }

@router.post("/stop")
def stop():
    scheduler = get_scheduler()
    scheduler.remove_job(JOB_ID)
    return {"status": "stopped"}

@router.get("/status")
def status(settings=Depends(get_settings)):
    scheduler = get_scheduler()
    job = scheduler.get_job(JOB_ID)
    return {
        "active": job is not None,
        "interval_seconds": settings.scan_interval_seconds,
        "next_run_at": job.next_run_time if job else None,
        "last_run_at": None,   # à enrichir via ScanState si besoin
    }
```

### Démarrage automatique optionnel

Si la variable d'environnement `CRON_AUTOSTART=true` est définie, le scheduler se lance automatiquement au démarrage de l'API (lifespan FastAPI) :

```python
# src/api/main.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    if settings.cron_autostart:
        # équivalent à POST /cron/start
        ...
    yield

app = FastAPI(lifespan=lifespan, ...)
```

Ajouter `cron_autostart: bool` dans `Settings` (`CRON_AUTOSTART`, défaut `False`).

---

## Acceptance criteria

- [ ] `POST /cron/start` lance un job APScheduler qui appelle `run_scan()` périodiquement
- [ ] `POST /cron/stop` stoppe le job sans crasher si déjà stoppé
- [ ] `GET /cron/status` retourne `active: true/false` et `next_run_at` correct
- [ ] Double `POST /cron/start` est idempotent (pas de doublon de job)
- [ ] `CRON_AUTOSTART=true` démarre le cron au boot de l'API
- [ ] L'ancien mode `python -m src.app` (boucle while) reste fonctionnel
