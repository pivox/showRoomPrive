from __future__ import annotations

import json
import re
from decimal import Decimal

from src.ai.providers.base import AIVerdict, BaseAIProvider
from src.config import Settings

_WEB_SEARCH_TOOL = {
    "name": "web_search",
    "description": (
        "Recherche des informations sur le web. "
        "Utilise cet outil pour trouver le prix historique et actuel d'un produit."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
}


class ClaudeProvider(BaseAIProvider):
    name = "claude"

    def __init__(self, settings: Settings):
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY non configurée")
        import anthropic
        self._client = anthropic.Anthropic(
            api_key=settings.anthropic_api_key,
        )
        self._settings = settings

    def verify(self, prompt: str) -> AIVerdict:
        import anthropic
        tools = [_WEB_SEARCH_TOOL] if self._settings.tavily_api_key else []
        messages = [{"role": "user", "content": prompt}]

        response = self._client.messages.create(
            model="claude-opus-4-7",
            max_tokens=2048,
            tools=tools,
            messages=messages,
        )

        while response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = self._handle_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
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
            snippets = [
                f"- {r['title']}: {r['content'][:300]} ({r['url']})"
                for r in result.get("results", [])
            ]
            return "\n".join(snippets) or "Aucun résultat."
        except Exception as exc:
            return f"Erreur recherche web: {exc}"

    @staticmethod
    def _parse_verdict(raw: str) -> AIVerdict:
        cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        data = json.loads(cleaned)
        rmp = data.get("real_market_price")
        return AIVerdict(
            is_real_deal=bool(data["is_real_deal"]),
            confidence=int(data.get("confidence", 50)),
            real_market_price=Decimal(str(rmp)) if rmp is not None else None,
            sources=data.get("sources", []),
            summary=data.get("summary", ""),
            raw_response=raw,
        )
