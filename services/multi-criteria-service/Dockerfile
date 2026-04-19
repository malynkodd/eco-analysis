FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY services/multi-criteria-service/requirements.txt /app/requirements.txt
COPY db/requirements.txt /app/db/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt -r /app/db/requirements.txt

COPY db /app/db
COPY services/multi-criteria-service /app/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
