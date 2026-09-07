# ==============================================================================
# QuantumAML Nexus - Multi-Stage Production Containerfile
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build & Dependency Wheel Cache
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install build dependencies for C-extensions and healthcheck tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install lightweight PyTorch CPU wheels to eliminate bloated CUDA binaries
RUN pip install --no-cache-dir --user torch --index-url https://download.pytorch.org/whl/cpu

# Layer-cached requirements installation
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# ------------------------------------------------------------------------------
# Stage 2: Hardened Runtime Container
# ------------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    PATH="/home/amluser/.local/bin:$PATH" \
    PYTHONPATH="/app"

# Install runtime OpenMP execution library and curl for healthcheck probes
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root system user and group (UID/GID 10001) for least privilege
RUN groupadd -g 10001 amluser && \
    useradd -u 10001 -g amluser -m -d /home/amluser -s /bin/bash amluser

# Copy pre-compiled dependencies from builder stage to user directory
COPY --from=builder /root/.local /home/amluser/.local

# Copy application code into /app/app (models are dynamically mounted at runtime)
COPY --chown=amluser:amluser app/ /app/app/

# Enforce secure ownership on /app directory
RUN chown -R amluser:amluser /app

# Switch to non-root execution context
USER amluser

# Expose HTTP serving port
EXPOSE 8000

# Healthcheck probe hitting /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production server entrypoint running Uvicorn with 4 workers
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
