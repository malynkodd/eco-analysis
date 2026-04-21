"""Re-export the shared persistence layer for backward compatibility."""

from db.base import Base, SessionLocal, engine, get_db, init_engine

__all__ = ["Base", "SessionLocal", "engine", "get_db", "init_engine"]
