# Steel.run Production Dockerfile
# Multi-stage build for security and optimization
FROM python:3.12-slim as builder

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies needed for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy dependency files and app structure for installation
COPY pyproject.toml ./
COPY app/ ./app/

# Install Python dependencies directly from pyproject.toml
RUN pip install .

# Production stage
FROM python:3.12-slim as production

# Security: Create non-root user
RUN groupadd -r steelrun && useradd -r -g steelrun steelrun

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/steelrun/.local/bin:$PATH" \
    ENV=production \
    PORT=8000

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create app directory and set ownership
RUN mkdir -p /app /app/logs /app/data && chown -R steelrun:steelrun /app

# Switch to app directory
WORKDIR /app

# Copy application code
COPY --chown=steelrun:steelrun app/ ./app/
COPY --chown=steelrun:steelrun migrations/ ./migrations/
COPY --chown=steelrun:steelrun alembic.ini ./
COPY --chown=steelrun:steelrun pyproject.toml ./

# Create startup script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Run database migrations if needed\n\
if [ "$RUN_MIGRATIONS" = "true" ]; then\n\
    echo "Running database migrations..."\n\
    alembic upgrade head\n\
fi\n\
\n\
# Start the application\n\
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WORKERS:-1}\n\
' > /app/start.sh && chmod +x /app/start.sh && chown steelrun:steelrun /app/start.sh

# Switch to non-root user
USER steelrun

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Set default command
CMD ["/app/start.sh"]

# Labels for metadata
LABEL maintainer="Steel.run Team <dev@steel.run>"
LABEL version="1.0.0"
LABEL description="Steel.run - Atomic Web Functions Platform"
LABEL org.opencontainers.image.title="Steel.run"
LABEL org.opencontainers.image.description="Transform natural language into web actions"
LABEL org.opencontainers.image.vendor="Steel.run"
LABEL org.opencontainers.image.version="1.0.0"