from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select

from src.api.deps import get_db, get_settings
from src.api.schemas.ai import AIJobListOut, AIJobOut, JobSummary, ResearchRequest, ResearchResponse
from src.models import AIJobStatus, AIResearchJob, Product

router = APIRouter()


def _ttl_cutoff(settings) -> datetime:
    return datetime.now(UTC) - timedelta(hours=settings.ai_result_ttl_hours)


def _job_to_out(job: AIResearchJob) -> AIJobOut:
    return AIJobOut(
        job_id=job.id,
        product_id=job.product_id,
        product_name=job.product.name,
        provider=job.provider,
        status=job.status.value,
        is_real_deal=job.is_real_deal,
        confidence=job.confidence,
        real_market_price=job.real_market_price,
        sources=job.sources,
        summary=job.summary,
        created_at=job.created_at,
        finished_at=job.finished_at,
    )


def _run_research_thread(product_id: int, job_id: int, settings) -> None:
    from src.ai.orchestrator import research_product
    from src.db import make_session_factory

    factory = make_session_factory(settings.database_url)
    with factory() as session:
        product = session.get(Product, product_id)
        job = session.get(AIResearchJob, job_id)
        if not product or not job:
            return
        research_product(product=product, session=session, settings=settings, existing_job=job)


@router.post("/research", status_code=202, response_model=ResearchResponse)
def launch_research(
    body: ResearchRequest,
    db=Depends(get_db),
    settings=Depends(get_settings),
):
    jobs_out: list[JobSummary] = []

    for product_id in body.product_ids:
        product = db.get(Product, product_id)
        if product is None:
            raise HTTPException(404, f"Produit {product_id} introuvable.")

        existing = db.execute(
            select(AIResearchJob)
            .where(AIResearchJob.product_id == product_id)
            .where(AIResearchJob.status == AIJobStatus.done)
            .where(AIResearchJob.finished_at >= _ttl_cutoff(settings))
            .order_by(desc(AIResearchJob.finished_at))
            .limit(1)
        ).scalar_one_or_none()

        if existing:
            jobs_out.append(JobSummary(job_id=existing.id, product_id=product_id, status="done"))
            continue

        job = AIResearchJob(
            product_id=product_id,
            provider="pending",
            status=AIJobStatus.pending,
        )
        db.add(job)
        db.flush()
        job_id = job.id
        db.commit()

        thread = threading.Thread(
            target=_run_research_thread,
            args=(product_id, job_id, settings),
            daemon=True,
        )
        thread.start()
        jobs_out.append(JobSummary(job_id=job_id, product_id=product_id, status="pending"))

    return ResearchResponse(jobs=jobs_out)


@router.get("/results/{job_id}", response_model=AIJobOut)
def get_result(job_id: int, db=Depends(get_db)):
    job = db.get(AIResearchJob, job_id)
    if job is None:
        raise HTTPException(404, "Job introuvable.")
    return _job_to_out(job)


@router.get("/results", response_model=AIJobListOut)
def list_results(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: str | None = None,
    product_id: int | None = None,
    db=Depends(get_db),
):
    base = select(AIResearchJob)
    if status:
        base = base.where(AIResearchJob.status == status)
    if product_id is not None:
        base = base.where(AIResearchJob.product_id == product_id)

    total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
    paged = base.order_by(desc(AIResearchJob.created_at)).offset((page - 1) * page_size).limit(page_size)
    items = db.execute(paged).scalars().all()

    return AIJobListOut(
        total=total,
        page=page,
        page_size=page_size,
        items=[_job_to_out(j) for j in items],
    )
