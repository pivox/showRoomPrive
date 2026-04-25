# TICKET-006 — AI Orchestrator + interface provider

**Epic:** AI Research Worker  
**Priorité:** P1  
**Complexité:** M  
**Dépendances:** TICKET-005

---

## Contexte

L'orchestrateur reçoit un produit, tente les providers IA dans l'ordre configuré (`AI_PROVIDER_ORDER`), persiste le résultat dans `ai_research_jobs`. Si un provider échoue, il passe au suivant (fallback). Chaque provider implémente une interface commune.

---

## Structure

```
src/ai/
  __init__.py
  orchestrator.py     ← ce ticket
  prompt.py           ← construction du prompt commun
  providers/
    __init__.py
    base.py           ← classe abstraite BaseAIProvider
    claude.py         ← TICKET-007
    openai.py         ← TICKET-008
    gemini.py         ← TICKET-009
```

---

## Interface provider (`src/ai/providers/base.py`)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

@dataclass
class AIVerdict:
    is_real_deal: bool
    confidence: int          # 0-100
    real_market_price: Decimal | None
    sources: list[str]
    summary: str
    raw_response: str

class BaseAIProvider(ABC):
    name: str                # "claude" | "openai" | "gemini"

    @abstractmethod
    def verify(self, prompt: str) -> AIVerdict:
        """Envoie le prompt et retourne un verdict structuré. Lève une exception si indisponible."""
        ...
```

---

## Prompt builder (`src/ai/prompt.py`)

```python
from src.models import Product

SYSTEM_PROMPT = """Tu es un expert en analyse de prix e-commerce français.
On te donne les informations d'un produit vendu sur Showroomprivé.
Effectue une recherche pour déterminer si la remise est réelle.
Réponds UNIQUEMENT en JSON valide, sans markdown, avec exactement ces champs :
{
  "is_real_deal": <bool>,
  "confidence": <int 0-100>,
  "real_market_price": <float ou null>,
  "sources": [<url>, ...],
  "summary": "<2-3 phrases>"
}"""

def build_prompt(product: Product) -> str:
    return f"""Produit à analyser :
- Nom : {product.name}
- Marque : {product.brand or "inconnue"}
- Prix Showroomprivé : {product.showroom_price} €
- Remise affichée : {product.displayed_discount or "non renseignée"}%
- Prix de référence détecté : {product.brand_price or "non disponible"} €
- URL produit : {product.product_url or "non disponible"}

Recherche le prix habituel de ce produit sur le web (historique 6 mois minimum),
compare avec les prix actuels chez d'autres revendeurs (Amazon, FNAC, site officiel marque...),
et détermine si la remise annoncée est réelle ou si le prix de référence est artificiel."""
```

---

## Orchestrateur (`src/ai/orchestrator.py`)

```python
from sqlalchemy.orm import Session
from datetime import datetime, UTC
from src.config import Settings
from src.models import Product, AIResearchJob, AIJobStatus
from src.ai.prompt import build_prompt, SYSTEM_PROMPT
from src.ai.providers.base import BaseAIProvider, AIVerdict

def _build_providers(settings: Settings) -> list[BaseAIProvider]:
    from src.ai.providers.claude import ClaudeProvider
    from src.ai.providers.openai import OpenAIProvider
    from src.ai.providers.gemini import GeminiProvider

    registry = {
        "claude": lambda: ClaudeProvider(settings),
        "openai": lambda: OpenAIProvider(settings),
        "gemini": lambda: GeminiProvider(settings),
    }
    order = [p.strip() for p in settings.ai_provider_order.split(",") if p.strip()]
    return [registry[name]() for name in order if name in registry]


def research_product(product: Product, session: Session, settings: Settings) -> AIResearchJob:
    """
    Crée un job, tente chaque provider, persiste le résultat.
    Retourne le job complété (ou en erreur si tous les providers échouent).
    """
    job = AIResearchJob(
        product_id=product.id,
        provider="pending",
        status=AIJobStatus.running,
    )
    session.add(job)
    session.flush()  # obtenir l'id sans commit

    providers = _build_providers(settings)
    if not providers:
        job.status = AIJobStatus.error
        job.raw_response = "Aucun provider IA configuré (AI_PROVIDER_ORDER vide ou clés manquantes)."
        job.finished_at = datetime.now(UTC)
        session.commit()
        return job

    prompt = build_prompt(product)
    last_error = None

    for provider in providers:
        try:
            verdict: AIVerdict = provider.verify(SYSTEM_PROMPT + "\n\n" + prompt)
            job.provider      = provider.name
            job.status        = AIJobStatus.done
            job.is_real_deal  = verdict.is_real_deal
            job.confidence    = verdict.confidence
            job.real_market_price = verdict.real_market_price
            job.sources       = verdict.sources
            job.summary       = verdict.summary
            job.raw_response  = verdict.raw_response
            job.finished_at   = datetime.now(UTC)
            session.commit()
            return job
        except Exception as exc:
            last_error = exc
            continue

    job.status = AIJobStatus.error
    job.raw_response = str(last_error)
    job.finished_at = datetime.now(UTC)
    session.commit()
    return job
```

### Nouvelles variables de config

Ajouter dans `Settings` et `load_settings()` :

```python
ai_provider_order: str  # AI_PROVIDER_ORDER, défaut "claude,openai,gemini"
anthropic_api_key: str  # ANTHROPIC_API_KEY, défaut ""
openai_api_key: str     # OPENAI_API_KEY, défaut ""
google_ai_api_key: str  # GOOGLE_AI_API_KEY, défaut ""
tavily_api_key: str     # TAVILY_API_KEY, défaut ""
```

---

## Acceptance criteria

- [ ] `research_product()` crée bien un `AIResearchJob` en DB avec status `running` puis `done` ou `error`
- [ ] Si le premier provider lève une exception, le second est essayé
- [ ] Si tous les providers échouent, le job est en `error` avec le message du dernier échec
- [ ] Si `AI_PROVIDER_ORDER` est vide, le job passe immédiatement en `error` avec un message explicite
- [ ] Le parsing JSON du verdict gère les cas où le LLM retourne du markdown autour du JSON (strip des ```json ``` blocks)
- [ ] `research_product()` est thread-safe (appelable depuis plusieurs threads simultanément pour des produits différents)
