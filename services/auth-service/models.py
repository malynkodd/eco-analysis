"""Re-export shared SQLAlchemy models. Single source of truth: ``db.models``."""
from db.models import User, UserRole

__all__ = ["User", "UserRole"]
