from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

JOB_ID = "showroom_scan"

_scheduler = BackgroundScheduler(timezone="UTC")
_scheduler.start()


def get_scheduler() -> BackgroundScheduler:
    return _scheduler
