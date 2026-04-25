from __future__ import annotations

import json
import re
from decimal import Decimal

from src.ai.providers.base import AIVerdict, BaseAIProvider
from src.config import Settings


class OpenAIProvider(BaseAIProvider):
    name = "openai"

    def __init__(self, settings: Settings):
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY non configurée")
        from openai import OpenAI
        self._client = OpenAI(api_key=settings.openai_api_key)

    def verify(self, prompt: str) -> AIVerdict:
        response = self._client.responses.create(
            model="gpt-4o",
            tools=[{"type": "web_search_preview"}],
            input=prompt,
        )
        raw = response.output_text
        sources = self._extract_sources(response)
        return self._parse_verdict(raw, sources)

    @staticmethod
    def _extract_sources(response) -> list[str]:
        sources: list[str] = []
        try:
            for item in response.output:
                annotations = getattr(item, "annotations", [])
                for ann in annotations:
                    url = getattr(ann, "url", None)
                    if url:
                        sources.append(url)
        except Exception:
            pass
        return sources

    @staticmethod
    def _parse_verdict(raw: str, extra_sources: list[str]) -> AIVerdict:
        cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        data = json.loads(cleaned)
        rmp = data.get("real_market_price")
        sources = list(dict.fromkeys(data.get("sources", []) + extra_sources))
        return AIVerdict(
            is_real_deal=bool(data["is_real_deal"]),
            confidence=int(data.get("confidence", 50)),
            real_market_price=Decimal(str(rmp)) if rmp is not None else None,
            sources=sources,
            summary=data.get("summary", ""),
            raw_response=raw,
        )
