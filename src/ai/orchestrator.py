from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from src.ai.prompt import SYSTEM_PROMPT, build_prompt
from src.ai.providers.base import AIVerdict, BaseAIProvider
from src.config import Settings
from src.models import AIJobStatus, AIResearchJob, Product


def _build_providers(settings: Settings) -> list[BaseAIProvider]:
    from src.ai.providers.claude import ClaudeProvider
    from src.ai.providers.gemini import GeminiProvider
    from src.ai.providers.openai import OpenAIProvider

    registry = {
        "claude": lambda: ClaudeProvider(settings),
        "openai": lambda: OpenAIProvider(settings),
        "gemini": lambda: GeminiProvider(settings),
    }
    order = [p.strip() for p in settings.ai_provider_order.split(",") if p.strip()]
    providers: list[BaseAIProvider] = []
    for name in order:
        if name not in registry:
            continue
        try:
            providers.append(registry[name]())
        except RuntimeError:
            pass
    return providers


def research_product(
    product: Product,
    session: Session,
    settings: Settings,
    existing_job: AIResearchJob | None = None,
) -> AIResearchJob:
    if existing_job is None:
        job = AIResearchJob(
            product_id=product.id,
            provider="pending",
            status=AIJobStatus.running,
        )
        session.add(job)
        session.flush()
    else:
        job = existing_job
        job.status = AIJobStatus.running
        session.flush()

    providers = _build_providers(settings)
    if not providers:
        job.status = AIJobStatus.error
        job.raw_response = "Aucun provider IA configuré (AI_PROVIDER_ORDER vide ou clés manquantes)."
        job.finished_at = datetime.now(UTC)
        session.commit()
        return job

    full_prompt = SYSTEM_PROMPT + "\n\n" + build_prompt(product)
    last_error: Exception | None = None

    for provider in providers:
        try:
            verdict: AIVerdict = provider.verify(full_prompt)
            job.provider = provider.name
            job.status = AIJobStatus.done
            job.is_real_deal = verdict.is_real_deal
            job.confidence = verdict.confidence
            job.real_market_price = verdict.real_market_price
            job.sources = verdict.sources
            job.summary = verdict.summary
            job.raw_response = verdict.raw_response
            job.finished_at = datetime.now(UTC)
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
