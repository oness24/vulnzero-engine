# Vulnerability Aggregator Service Dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY services/aggregator/ ./services/aggregator/

RUN useradd -m -u 1000 vulnzero && \
    chown -R vulnzero:vulnzero /app

USER vulnzero

# This service runs as part of Celery workers
CMD ["echo", "Aggregator service - runs via Celery tasks"]
