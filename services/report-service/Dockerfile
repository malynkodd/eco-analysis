# syntax=docker/dockerfile:1.6

# ─── builder ──────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

COPY services/report-service/requirements.txt requirements.txt
COPY db/requirements.txt db-requirements.txt
COPY eco_common/requirements.txt eco-common-requirements.txt

RUN pip install --prefix=/install \
        -r requirements.txt \
        -r db-requirements.txt \
        -r eco-common-requirements.txt

# ─── runtime ──────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# matplotlib + reportlab need libfreetype/libpng at runtime (wheels pull headers).
RUN apt-get update \
 && apt-get install -y --no-install-recommends libfreetype6 libpng16-16 \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/install/bin:$PATH \
    PYTHONPATH=/install/lib/python3.11/site-packages \
    MPLCONFIGDIR=/tmp/matplotlib \
    WORKERS=4

RUN groupadd --system --gid 1001 app \
 && useradd  --system --uid 1001 --gid app --home-dir /app --shell /sbin/nologin app

WORKDIR /app

COPY --from=builder /install /install
COPY db /app/db
COPY eco_common /app/eco_common
COPY services/report-service /app/

RUN mkdir -p /tmp/matplotlib && chown -R app:app /app /tmp/matplotlib

USER 1001
EXPOSE 8000

CMD ["sh", "-c", "exec gunicorn main:app \
      --bind 0.0.0.0:8000 \
      --worker-class uvicorn.workers.UvicornWorker \
      --workers ${WORKERS:-4} \
      --timeout 120 \
      --graceful-timeout 30 \
      --access-logfile - --error-logfile -"]
