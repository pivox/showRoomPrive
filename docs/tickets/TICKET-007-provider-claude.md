# TICKET-007 — Provider Claude (Anthropic)

**Epic:** AI Research Worker  
**Priorité:** P1  
**Complexité:** M  
**Dépendances:** TICKET-006

---

## Contexte

Claude (claude-opus-4-7) supporte le tool use natif. Pour la recherche web on passe par un tool `web_search` implémenté via l'API Tavily (ou Brave Search). Le provider doit parser la réponse JSON du LLM et retourner un `AIVerdict`.

---

## Dépendances Python

```
anthropic==0.40.0
tavily-python==0.5.0   # si TAVILY_API_KEY est défini
```

---

## Implémentation (`src/ai/providers/claude.py`)

```python
import json
import re
from decimal import Decimal
import anthropic
from src.ai.providers.base import BaseAIProvider, AIVerdict
from src.config import Settings

WEB_SEARCH_TOOL = {
    "name": "web_search",
    "description": "Recherche des informations sur le web. Utilise cet outil pour trouver le prix historique et actuel d'un produit.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "La requête de recherche"}
        },
        "required": ["query"],
    },
}

class ClaudeProvider(BaseAIProvider):
    name = "claude"

    def __init__(self, settings: Settings):
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY non configurée")
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._settings = settings

    def verify(self, prompt: str) -> AIVerdict:
        messages = [{"role": "user", "content": prompt}]
        tools = [WEB_SEARCH_TOOL] if self._settings.tavily_api_key else []

        response = self._client.messages.create(
            model="claude-opus-4-7",
            max_tokens=2048,
            tools=tools,
            messages=messages,
        )

        # Agentic loop : résoudre les appels d'outils
        while response.stop_reason == "tool_use":
            tool_uses = [b for b in response.content if b.type == "tool_use"]
            tool_results = []
            for tool_use in tool_uses:
                result = self._handle_tool(tool_use.name, tool_use.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result,
                })
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
            response = self._client.messages.create(
                model="claude-opus-4-7",
                max_tokens=2048,
                tools=tools,
                messages=messages,
            )

        raw = next(
            (b.text for b in response.content if hasattr(b, "text")),
            "",
        )
        return self._parse_verdict(raw)

    def _handle_tool(self, name: str, inputs: dict) -> str:
        if name == "web_search":
            return self._web_search(inputs.get("query", ""))
        return "Outil inconnu"

    def _web_search(self, query: str) -> str:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=self._settings.tavily_api_key)
            result = client.search(query, max_results=5)
            snippets = [f"- {r['title']}: {r['content'][:300]} ({r['url']})"
                        for r in result.get("results", [])]
            return "\n".join(snippets) or "Aucun résultat."
        except Exception as exc:
            return f"Erreur recherche web: {exc}"

    @staticmethod
    def _parse_verdict(raw: str) -> AIVerdict:
        # Strip markdown code blocks si présents
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

## Notes d'implémentation

- **Prompt caching** : si la même analyse est relancée pour le même produit dans les 5 minutes, retourner le dernier job `done` en DB plutôt que de re-appeler l'API (à implémenter dans l'orchestrateur, pas dans le provider).
- **Timeout** : passer `timeout=httpx.Timeout(60.0)` au client Anthropic (les tool loops peuvent être longues).
- **Rate limit** : ne pas gérer dans le provider — l'orchestrateur doit être appelé séquentiellement ou avec un semaphore.

---

## Acceptance criteria

- [ ] Avec une `ANTHROPIC_API_KEY` valide, le provider retourne un `AIVerdict` parsé
- [ ] Sans `ANTHROPIC_API_KEY`, le constructeur lève `RuntimeError` (le provider est sauté par l'orchestrateur)
- [ ] La boucle tool use se termine même si Claude enchaîne plusieurs appels `web_search`
- [ ] Un JSON renvoyé dans un bloc markdown ```json est correctement parsé
- [ ] Un JSON invalide lève une exception explicite (pas un crash silencieux)
