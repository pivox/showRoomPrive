from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


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


class AIJobListOut(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AIJobOut]
