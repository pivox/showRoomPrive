from __future__ import annotations

import json
import re
from decimal import Decimal

from src.ai.providers.base import AIVerdict, BaseAIProvider
from src.config import Settings


class GeminiProvider(BaseAIProvider):
    name = "gemini"

    def __init__(self, settings: Settings):
        if not settings.google_ai_api_key:
            raise RuntimeError("GOOGLE_AI_API_KEY non configurée")
        from google import genai
        self._client = genai.Client(api_key=settings.google_ai_api_key)

    def verify(self, prompt: str) -> AIVerdict:
        from google.genai import types
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
        sources: list[str] = []
        try:
            for candidate in response.candidates:
                grounding = getattr(candidate, "grounding_metadata", None)
                if grounding and grounding.grounding_chunks:
                    for chunk in grounding.grounding_chunks:
                        web = getattr(chunk, "web", None)
                        if web and web.uri:
                            sources.append(web.uri)
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
