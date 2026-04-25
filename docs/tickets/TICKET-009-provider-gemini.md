# TICKET-009 — Provider Gemini (Google AI)

**Epic:** AI Research Worker  
**Priorité:** P2  
**Complexité:** S  
**Dépendances:** TICKET-006

---

## Contexte

Gemini 2.0 Flash supporte le grounding natif via Google Search, ce qui permet d'obtenir des informations fraîches sans API tierce. C'est le provider le moins coûteux des trois.

---

## Dépendances Python

```
google-genai==1.0.0
```

---

## Implémentation (`src/ai/providers/gemini.py`)

```python
import json
import re
from decimal import Decimal
from google import genai
from google.genai import types
from src.ai.providers.base import BaseAIProvider, AIVerdict
from src.config import Settings


class GeminiProvider(BaseAIProvider):
    name = "gemini"

    def __init__(self, settings: Settings):
        if not settings.google_ai_api_key:
            raise RuntimeError("GOOGLE_AI_API_KEY non configurée")
        self._client = genai.Client(api_key=settings.google_ai_api_key)

    def verify(self, prompt: str) -> AIVerdict:
        response = self._client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.2,
            ),
        )
        raw = response.text
        sources = self._extract_sources(response)
        return self._parse_verdict(raw, sources)

    @staticmethod
    def _extract_sources(response) -> list[str]:
        sources = []
        try:
            for candidate in response.candidates:
                grounding = getattr(candidate, "grounding_metadata", None)
                if grounding and grounding.grounding_chunks:
                    for chunk in grounding.grounding_chunks:
                        if hasattr(chunk, "web") and chunk.web.uri:
                            sources.append(chunk.web.uri)
        except Exception:
            pass
        return sources

    @staticmethod
    def _parse_verdict(raw: str, extra_sources: list[str]) -> AIVerdict:
        cleaned = re.sub(r"```(?:json)?", "", raw).strip()
        data = json.loads(cleaned)
        sources = list(dict.fromkeys(data.get("sources", []) + extra_sources))
        return AIVerdict(
            is_real_deal=bool(data["is_real_deal"]),
            confidence=int(data.get("confidence", 50)),
            real_market_price=Decimal(str(data["real_market_price"])) if data.get("real_market_price") else None,
            sources=sources,
            summary=data.get("summary", ""),
            raw_response=raw,
        )
```

---

## Acceptance criteria

- [ ] Avec une `GOOGLE_AI_API_KEY` valide, retourne un `AIVerdict` parsé
- [ ] Sans clé, le constructeur lève `RuntimeError`
- [ ] Les URLs du grounding Google Search sont incluses dans `sources` (dédupliquées)
- [ ] Parsing JSON robuste (strip markdown)
