from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class ScanState:
    scan_id: str = ""
    status: str = "idle"  # idle | running | done | error
    started_at: datetime | None = None
    finished_at: datetime | None = None
    products_found: int | None = None
    error: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


_state = ScanState()


def get_state() -> ScanState:
    return _state
