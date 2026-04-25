# TICKET-002 — Router /scan (run + status)

**Epic:** Backend API Foundation  
**Priorité:** P0  
**Complexité:** M  
**Dépendances:** TICKET-001

---

## Contexte

Le scan (scrape → validate → score → upsert) doit être déclenchable via l'API sans avoir à SSH sur le serveur. Un seul scan peut tourner à la fois. Le frontend a besoin de connaître l'état en temps réel.

---

## Endpoints

### `POST /scan/run`

Déclenche un scan immédiat en arrière-plan.

**Réponse 202 :**
```json
{ "status": "started", "scan_id": "uuid4" }
```

**Réponse 409 si un scan tourne déjà :**
```json
{ "detail": "Un scan est déjà en cours." }
```

---

### `GET /scan/status`

Retourne l'état du scan en cours (ou du dernier scan terminé).

**Réponse 200 :**
```json
{
  "scan_id": "uuid4",
  "status": "running",          // "idle" | "running" | "done" | "error"
  "started_at": "2026-04-25T10:00:00Z",
  "finished_at": null,
  "products_found": null,       // nombre de produits scrapés, disponible à la fin
  "error": null                 // message d'erreur si status = "error"
}
```

---

## Implémentation

### State management

Utiliser un objet singleton en mémoire pour le state du scan (suffisant, pas besoin de Redis pour l'instant) :

```python
# src/api/scan_state.py
import threading
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

@dataclass
class ScanState:
    scan_id: str = ""
    status: str = "idle"          # idle | running | done | error
    started_at: datetime | None = None
    finished_at: datetime | None = None
    products_found: int | None = None
    error: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

_state = ScanState()

def get_state() -> ScanState:
    return _state
```

### Router

```python
# src/api/routers/scan.py
import threading
from fastapi import APIRouter, HTTPException, Depends
from src.api.scan_state import get_state
from src.api.deps import get_settings
from src.app import run_scan

router = APIRouter()

def _run_in_background(state, settings):
    try:
        products = run_scan()        # run_scan() doit retourner le count
        with state._lock:
            state.status = "done"
            state.products_found = products
            state.finished_at = datetime.now(UTC)
    except Exception as exc:
        with state._lock:
            state.status = "error"
            state.error = str(exc)
            state.finished_at = datetime.now(UTC)

@router.post("/run", status_code=202)
def run(settings=Depends(get_settings)):
    state = get_state()
    with state._lock:
        if state.status == "running":
            raise HTTPException(409, "Un scan est déjà en cours.")
        state.scan_id = str(uuid4())
        state.status = "running"
        state.started_at = datetime.now(UTC)
        state.finished_at = None
        state.products_found = None
        state.error = None

    thread = threading.Thread(target=_run_in_background, args=(state, settings), daemon=True)
    thread.start()
    return {"status": "started", "scan_id": state.scan_id}

@router.get("/status")
def status():
    state = get_state()
    return {
        "scan_id": state.scan_id,
        "status": state.status,
        "started_at": state.started_at,
        "finished_at": state.finished_at,
        "products_found": state.products_found,
        "error": state.error,
    }
```

### Modification de `src/app.py`

`run_scan()` doit retourner le nombre de produits traités :

```python
def run_scan() -> int:
    ...
    # à la fin, après session.commit()
    return len(scraped_products)
```

---

## Acceptance criteria

- [ ] `POST /scan/run` retourne 202 et lance le scan en arrière-plan
- [ ] Un second `POST /scan/run` pendant un scan retourne 409
- [ ] `GET /scan/status` retourne `"running"` pendant le scan, puis `"done"` avec `products_found`
- [ ] Si le scan échoue, `status = "error"` et `error` contient le message
- [ ] Le scan CLI (`python -m src.app --once`) fonctionne toujours
