from __future__ import annotations

from datetime import UTC, datetime

from apscheduler.triggers.interval import IntervalTrigger
from fastapi import APIRouter, Depends

from src.api.deps import get_settings
from src.api.scheduler import JOB_ID, get_scheduler
from src.config import Settings

router = APIRouter()


def _start_cron(settings: Settings) -> None:
    from src.app import run_scan
    scheduler = get_scheduler()
    scheduler.add_job(
        run_scan,
        trigger=IntervalTrigger(seconds=settings.scan_interval_seconds),
        id=JOB_ID,
        replace_existing=True,
        next_run_time=datetime.now(UTC),
    )


@router.post("/start")
def start(settings: Settings = Depends(get_settings)):
    scheduler = get_scheduler()
    job = scheduler.get_job(JOB_ID)
    if job is None:
        _start_cron(settings)
        job = scheduler.get_job(JOB_ID)
    return {
        "status": "started",
        "interval_seconds": settings.scan_interval_seconds,
        "next_run_at": job.next_run_time if job else None,
    }


@router.post("/stop")
def stop():
    scheduler = get_scheduler()
    if scheduler.get_job(JOB_ID):
        scheduler.remove_job(JOB_ID)
    return {"status": "stopped"}


@router.get("/status")
def status(settings: Settings = Depends(get_settings)):
    scheduler = get_scheduler()
    job = scheduler.get_job(JOB_ID)
    return {
        "active": job is not None,
        "interval_seconds": settings.scan_interval_seconds,
        "next_run_at": job.next_run_time if job else None,
    }
