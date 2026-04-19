# syntax=docker/dockerfile:1.6

# ─── builder ──────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

COPY services/scenario-service/requirements.txt requirements.txt
COPY db/requirements.txt db-requirements.txt
COPY eco_common/requirements.txt eco-common-requirements.txt

RUN pip install --prefix=/install \
        -r requirements.txt \
        -r db-requirements.txt \
        -r eco-common-requirements.txt

# ─── runtime ──────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/install/bin:$PATH \
    PYTHONPATH=/install/lib/python3.11/site-packages \
    WORKERS=4

RUN groupadd --system --gid 1001 app \
 && useradd  --system --uid 1001 --gid app --home-dir /app --shell /sbin/nologin app

WORKDIR /app

COPY --from=builder /install /install
COPY db /app/db
COPY eco_common /app/eco_common
COPY services/scenario-service /app/

RUN chown -R app:app /app

USER 1001
EXPOSE 8000

CMD ["sh", "-c", "exec gunicorn main:app \
      --bind 0.0.0.0:8000 \
      --worker-class uvicorn.workers.UvicornWorker \
      --workers ${WORKERS:-4} \
      --timeout 60 \
      --graceful-timeout 30 \
      --access-logfile - --error-logfile -"]
