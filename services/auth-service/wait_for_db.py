"""Block until PostgreSQL accepts a connection. Run before service start."""

from db.base import init_engine

if __name__ == "__main__":
    init_engine()
    print("Database is ready.")
