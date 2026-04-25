# TICKET-008 — Provider OpenAI (GPT-4o)

**Epic:** AI Research Worker  
**Priorité:** P2  
**Complexité:** S  
**Dépendances:** TICKET-006

---

## Contexte

GPT-4o via l'API Responses d'OpenAI supporte nativement l'outil `web_search_preview`, sans avoir besoin d'une API de recherche tierce. C'est le provider le plus simple à intégrer pour la recherche web.

---

## Dépendances Python

```
openai==1.35.0
```

---

## Implémentation (`src/ai/providers/openai.py`)

```python
import json
import re
from decimal import Decimal
from openai import OpenAI
from src.ai.providers.base import BaseAIProvider, AIVerdict
from src.config import Settings


class OpenAIProvider(BaseAIProvider):
    name = "openai"

    def __init__(self, settings: Settings):
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY non configurée")
        self._client = OpenAI(api_key=settings.openai_api_key)

    def verify(self, prompt: str) -> AIVerdict:
        response = self._client.responses.create(
            model="gpt-4o",
            tools=[{"type": "web_search_preview"}],
            input=prompt,
        )
        raw = response.output_text
        return self._parse_verdict(raw)

    @staticmethod
    def _parse_verdict(raw: str) -> AIVerdict:
        cleaned = re.sub(r"```(?:json)?", "", raw).strip()
        data = json.loads(cleaned)
        return AIVerdict(
            is_real_deal=bool(data["is_real_deal"]),
            confidence=int(data.get("confidence", 50)),
            real_market_price=Decimal(str(data["real_market_price"])) if data.get("real_market_price") else None,
            sources=data.get("sources", []),
            summary=data.get("summary", ""),
            raw_response=raw,
        )
```

---

## Notes

- Le modèle `gpt-4o` avec `web_search_preview` fait la recherche automatiquement ; pas de boucle tool use à gérer.
- Les sources retournées par GPT-4o sont dans `response.output` (annotations) — les extraire si disponibles et les injecter dans `sources` du verdict avant le parsing JSON.

```python
# Extraction des URLs depuis les annotations
sources = []
for item in response.output:
    if hasattr(item, "annotations"):
        for ann in item.annotations:
            if hasattr(ann, "url"):
                sources.append(ann.url)
# Merger avec les sources du JSON si présentes
```

---

## Acceptance criteria

- [ ] Avec une `OPENAI_API_KEY` valide, retourne un `AIVerdict` parsé
- [ ] Sans clé, le constructeur lève `RuntimeError`
- [ ] Les URLs des annotations OpenAI sont incluses dans `sources`
- [ ] Parsing JSON robuste (strip markdown)
