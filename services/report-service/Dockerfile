FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY services/report-service/requirements.txt /app/requirements.txt
COPY db/requirements.txt /app/db/requirements.txt
COPY eco_common/requirements.txt /app/eco_common/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt -r /app/db/requirements.txt -r /app/eco_common/requirements.txt

COPY db /app/db
COPY eco_common /app/eco_common
COPY services/report-service /app/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
