from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from src.config import Settings, load_settings
from src.db import make_session_factory


def get_settings() -> Settings:
    return load_settings()


def get_db(settings: Settings = Depends(get_settings)) -> Generator[Session, None, None]:
    factory = make_session_factory(settings.database_url)
    with factory() as session:
        yield session
