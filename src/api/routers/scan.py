from __future__ import annotations

import threading
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import get_settings
from src.api.scan_state import get_state

router = APIRouter()


def _run_in_background(settings) -> None:
    from src.app import run_scan
    state = get_state()
    try:
        count = run_scan()
        with state._lock:
            state.status = "done"
            state.products_found = count
            state.finished_at = datetime.now(UTC)
    except Exception as exc:
        with state._lock:
            state.status = "error"
            state.error = str(exc)
            state.finished_at = datetime.now(UTC)


@router.post("/run", status_code=202)
def run_scan_endpoint(settings=Depends(get_settings)):
    state = get_state()
    with state._lock:
        if state.status == "running":
            raise HTTPException(409, "Un scan est déjà en cours.")
        state.scan_id = str(uuid4())
        state.status = "running"
        state.started_at = datetime.now(UTC)
        state.finished_at = None
        state.products_found = None
        state.error = None

    thread = threading.Thread(
        target=_run_in_background,
        args=(settings,),
        daemon=True,
    )
    thread.start()
    return {"status": "started", "scan_id": state.scan_id}


@router.get("/status")
def scan_status():
    state = get_state()
    return {
        "scan_id": state.scan_id,
        "status": state.status,
        "started_at": state.started_at,
        "finished_at": state.finished_at,
        "products_found": state.products_found,
        "error": state.error,
    }
