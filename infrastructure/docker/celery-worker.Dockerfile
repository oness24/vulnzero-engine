# Celery Worker Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules
COPY shared/ ./shared/

# Copy all service code (workers need access to all services)
COPY services/ ./services/

# Create non-root user
RUN useradd -m -u 1000 vulnzero && \
    chown -R vulnzero:vulnzero /app

USER vulnzero

# Default command (can be overridden in docker-compose)
CMD ["celery", "-A", "shared.celery_app", "worker", "--loglevel=info"]
