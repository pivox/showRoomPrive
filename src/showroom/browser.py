from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from playwright.sync_api import BrowserContext, sync_playwright


def ensure_parent(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def context_with_persisted_state(
    headless: bool,
    storage_state_path: str,
) -> Iterator[BrowserContext]:
    ensure_parent(storage_state_path)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        storage_state = storage_state_path if os.path.exists(storage_state_path) else None
        context = browser.new_context(storage_state=storage_state)
        try:
            yield context
        finally:
            context.storage_state(path=storage_state_path)
            context.close()
            browser.close()
