# Madan Sara Microservice - Multi-stage Docker build
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment in a shared location
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY . .

# Make sure scripts are executable
RUN chmod +x scripts/*.sh || true

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

# Update PATH (must be after USER directive to affect the user's environment)
ENV PATH="/opt/venv/bin:$PATH"

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8002}/health || exit 1

# Expose port (Railway will override with $PORT)
EXPOSE 8002

# Start command (Railway will override this)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
