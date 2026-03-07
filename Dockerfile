# TechCorp FTE Multi-stage Dockerfile
# Stage 1: Builder - Install dependencies
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Stage 2: Production - Runtime image
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app"

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    netcat-traditional \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r fte && useradd -r -g fte fte

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create application directory
WORKDIR /app

# Create necessary directories
RUN mkdir -p /app/logs /app/temp && \
    chown -R fte:fte /app

# Copy application code
COPY --chown=fte:fte production/ ./production/
COPY --chown=fte:fte context/ ./context/
COPY --chown=fte:fte scripts/ ./scripts/
COPY --chown=fte:fte .env.example .env.example

# Set ownership
RUN chown -R fte:fte /app

# Switch to non-root user
USER fte

# Health check script
COPY --from=builder /opt/venv/bin/python /usr/local/bin/
RUN echo '#!/bin/bash\n\
curl -f http://localhost:8000/health || exit 1\n\
' > /app/healthcheck.sh && \
chmod +x /app/healthcheck.sh

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "production.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Labels
LABEL maintainer="TechCorp FTE Team" \
      version="1.0.0" \
      description="TechCorp Customer Success FTE" \
      org.opencontainers.image.source="https://github.com/techcorp/fte"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /app/healthcheck.sh
