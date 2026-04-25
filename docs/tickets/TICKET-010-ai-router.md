# TICKET-010 — Router /ai (déclencher et consulter les analyses)

**Epic:** AI Research Worker  
**Priorité:** P1  
**Complexité:** M  
**Dépendances:** TICKET-005, TICKET-006

---

## Contexte

Le frontend doit pouvoir lancer une analyse IA sur un ou plusieurs produits et suivre l'avancement des jobs en polling. Les jobs tournent en arrière-plan (threads) pour ne pas bloquer la réponse HTTP.

---

## Endpoints

### `POST /ai/research`

Lance une analyse IA pour un ou plusieurs produits.

**Body :**
```json
{ "product_ids": [1, 2, 3] }
```

**Réponse 202 :**
```json
{
  "jobs": [
    { "job_id": 42, "product_id": 1, "status": "pending" },
    { "job_id": 43, "product_id": 2, "status": "pending" },
    { "job_id": 44, "product_id": 3, "status": "pending" }
  ]
}
```

**Règles métier :**
- Si un produit a déjà un job `done` créé dans les dernières `AI_RESULT_TTL_HOURS` heures (défaut 24h), ne pas relancer — retourner le job existant avec son statut.
- Maximum 10 produits par requête (429 sinon).
- Si un `product_id` n'existe pas en DB, retourner 404 avec les IDs invalides.

---

### `GET /ai/results/{job_id}`

Retourne le détail d'un job IA.

**Réponse 200 :**
```json
{
  "job_id": 42,
  "product_id": 1,
  "product_name": "Sac cuir Milano",
  "provider": "claude",
  "status": "done",
  "is_real_deal": true,
  "confidence": 82,
  "real_market_price": 240.00,
  "sources": ["https://amazon.fr/...", "https://fnac.com/..."],
  "summary": "Le prix habituel de ce sac est autour de 230-250€. La remise de 64% est confirmée par plusieurs sources.",
  "created_at": "2026-04-25T10:00:00Z",
  "finished_at": "2026-04-25T10:00:45Z"
}
```

**Réponse 404** si job inexistant.

---

### `GET /ai/results`

Liste les jobs récents (pour la vue historique du frontend).

**Query params :** `page`, `page_size`, `status`, `product_id`

**Réponse 200 :** liste paginée (même structure que `/products`).

---

## Implémentation

### Schéma Pydantic

```python
# src/api/schemas/ai.py
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime

class ResearchRequest(BaseModel):
    product_ids: list[int] = Field(..., min_length=1, max_length=10)

class JobSummary(BaseModel):
    job_id: int
    product_id: int
    status: str

class ResearchResponse(BaseModel):
    jobs: list[JobSummary]

class AIJobOut(BaseModel):
    job_id: int
    product_id: int
    product_name: str
    provider: str
    status: str
    is_real_deal: bool | None
    confidence: int | None
    real_market_price: Decimal | None
    sources: list[str] | None
    summary: str | None
    created_at: datetime
    finished_at: datetime | None

    model_config = {"from_attributes": True}
```

### Router

```python
# src/api/routers/ai.py
import threading
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from src.api.deps import get_db, get_settings
from src.api.schemas.ai import ResearchRequest, ResearchResponse, AIJobOut
from src.models import Product, AIResearchJob, AIJobStatus
from src.ai.orchestrator import research_product
from datetime import datetime, UTC, timedelta

router = APIRouter()

def _ttl_cutoff(settings) -> datetime:
    hours = getattr(settings, "ai_result_ttl_hours", 24)
    return datetime.now(UTC) - timedelta(hours=hours)

@router.post("/research", status_code=202, response_model=ResearchResponse)
def launch_research(body: ResearchRequest, db=Depends(get_db), settings=Depends(get_settings)):
    jobs_out = []

    for product_id in body.product_ids:
        product = db.get(Product, product_id)
        if product is None:
            raise HTTPException(404, f"Produit {product_id} introuvable.")

        # Vérifier TTL
        existing = db.execute(
            select(AIResearchJob)
            .where(AIResearchJob.product_id == product_id)
            .where(AIResearchJob.status == AIJobStatus.done)
            .where(AIResearchJob.finished_at >= _ttl_cutoff(settings))
            .order_by(AIResearchJob.finished_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        if existing:
            jobs_out.append(JobSummary(job_id=existing.id, product_id=product_id, status="done"))
            continue

        # Créer job pending et lancer en background
        job = AIResearchJob(product_id=product_id, provider="pending", status=AIJobStatus.pending)
        db.add(job)
        db.flush()
        job_id = job.id
        db.commit()

        thread = threading.Thread(
            target=_run_research,
            args=(product_id, job_id, settings),
            daemon=True,
        )
        thread.start()
        jobs_out.append(JobSummary(job_id=job_id, product_id=product_id, status="pending"))

    return ResearchResponse(jobs=jobs_out)


def _run_research(product_id: int, job_id: int, settings):
    """Exécuté dans un thread séparé — crée sa propre session DB."""
    from src.db import make_session_factory
    factory = make_session_factory(settings.database_url)
    with factory() as session:
        product = session.get(Product, product_id)
        job = session.get(AIResearchJob, job_id)
        if not product or not job:
            return
        research_product(product=product, session=session, settings=settings, existing_job=job)


@router.get("/results/{job_id}", response_model=AIJobOut)
def get_result(job_id: int, db=Depends(get_db)):
    job = db.get(AIResearchJob, job_id)
    if job is None:
        raise HTTPException(404, "Job introuvable.")
    return _to_out(job)

def _to_out(job: AIResearchJob) -> AIJobOut:
    return AIJobOut(
        job_id=job.id,
        product_id=job.product_id,
        product_name=job.product.name,
        provider=job.provider,
        status=job.status,
        is_real_deal=job.is_real_deal,
        confidence=job.confidence,
        real_market_price=job.real_market_price,
        sources=job.sources,
        summary=job.summary,
        created_at=job.created_at,
        finished_at=job.finished_at,
    )
```

### Nouvelle variable de config

```python
ai_result_ttl_hours: int  # AI_RESULT_TTL_HOURS, défaut 24
```

---

## Acceptance criteria

- [ ] `POST /ai/research` avec des IDs valides retourne 202 et crée les jobs en DB
- [ ] Un produit avec un job `done` récent (< TTL) n'est pas relancé
- [ ] `POST /ai/research` avec un ID inexistant retourne 404
- [ ] Plus de 10 IDs retourne 422
- [ ] `GET /ai/results/{id}` retourne le job avec le nom du produit
- [ ] `GET /ai/results/{id}` pendant l'exécution retourne `status: "running"`
- [ ] La session DB du thread background est indépendante de la session HTTP
