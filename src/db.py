from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.models import Base


def make_engine(database_url: str):
    return create_engine(database_url, pool_pre_ping=True)


def make_session_factory(database_url: str) -> sessionmaker[Session]:
    engine = make_engine(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db(database_url: str) -> None:
    engine = make_engine(database_url)
    Base.metadata.create_all(bind=engine)

