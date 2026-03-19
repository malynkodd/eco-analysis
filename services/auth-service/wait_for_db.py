import time
import os
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

DATABASE_URL = os.getenv("DATABASE_URL")


def wait_for_db():
    """Чекаємо поки PostgreSQL буде готовий приймати з'єднання"""
    print("⏳ Очікуємо підключення до бази даних...")
    retries = 30  # максимум 30 спроб

    for attempt in range(retries):
        try:
            engine = create_engine(DATABASE_URL)
            # Пробуємо підключитись
            with engine.connect() as conn:
                print("✅ База даних готова!")
                return
        except OperationalError:
            print(f"   Спроба {attempt + 1}/{retries} — БД ще не готова, чекаємо 2 сек...")
            time.sleep(2)

    print("❌ Не вдалось підключитись до БД після 30 спроб")
    raise Exception("Database connection failed")


if __name__ == "__main__":
    wait_for_db()