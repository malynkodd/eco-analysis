"""Engine, session factory, and declarative base.

The engine is created lazily on first call to ``init_engine`` (or first
access through ``engine`` / ``SessionLocal``) so the package can be
imported in environments without a database (e.g. unit tests for pure
calculator code).
"""
from __future__ import annotations

import os
import time
from typing import Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Single declarative base shared by every model in the project."""


_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker[Session]] = None


def init_engine(
    url: Optional[str] = None,
    *,
    retries: int = 10,
    delay_seconds: float = 3.0,
) -> Engine:
    """Build the engine and bind ``SessionLocal``. Idempotent."""
    global _engine, _SessionLocal
    if _engine is not None:
        return _engine

    database_url = url or os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")

    last_exc: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            eng = create_engine(database_url, pool_pre_ping=True, future=True)
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            _engine = eng
            _SessionLocal = sessionmaker(
                bind=eng, autocommit=False, autoflush=False, future=True
            )
            return eng
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(delay_seconds)
            else:
                raise RuntimeError(
                    f"Could not connect to database after {retries} attempts: {exc}"
                ) from last_exc
    raise RuntimeError("unreachable")


class _LazyEngine:
    """Proxy that calls ``init_engine`` on first attribute access."""

    def __getattr__(self, name: str):
        return getattr(init_engine(), name)


class _LazySessionLocal:
    """Proxy that defers session-factory construction to first call."""

    def __call__(self, *args, **kwargs) -> Session:
        if _SessionLocal is None:
            init_engine()
        assert _SessionLocal is not None
        return _SessionLocal(*args, **kwargs)


engine = _LazyEngine()
SessionLocal = _LazySessionLocal()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a SQLAlchemy session."""
    if _SessionLocal is None:
        init_engine()
    assert _SessionLocal is not None
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
