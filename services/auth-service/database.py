"""Re-export the shared persistence layer for backward compatibility.

All real definitions live in ``db.base`` and ``db.models``.
"""
from db.base import Base, SessionLocal, engine, get_db, init_engine

__all__ = ["Base", "SessionLocal", "engine", "get_db", "init_engine"]
