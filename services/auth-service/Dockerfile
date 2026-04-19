FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY services/auth-service/requirements.txt /app/requirements.txt
COPY db/requirements.txt /app/db/requirements.txt
COPY eco_common/requirements.txt /app/eco_common/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt -r /app/db/requirements.txt -r /app/eco_common/requirements.txt

COPY db /app/db
COPY eco_common /app/eco_common
COPY services/auth-service /app/

CMD ["sh", "-c", "python wait_for_db.py && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"]
