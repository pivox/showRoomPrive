from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class AIVerdict:
    is_real_deal: bool
    confidence: int
    real_market_price: Decimal | None
    sources: list[str]
    summary: str
    raw_response: str


class BaseAIProvider(ABC):
    name: str

    @abstractmethod
    def verify(self, prompt: str) -> AIVerdict:
        """Send prompt and return a structured verdict. Raise on failure."""
        ...
