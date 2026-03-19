import os
import time
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

def create_engine_with_retry(url, retries=10, delay=3):
    for attempt in range(retries):
        try:
            eng = create_engine(url, pool_pre_ping=True)
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            return eng
        except Exception as e:
            if attempt < retries - 1:
                print(f"DB not ready (attempt {attempt + 1}/{retries}): {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                raise

engine = create_engine_with_retry(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()