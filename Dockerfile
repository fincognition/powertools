FROM python:3.12-slim

WORKDIR /app

# Install uv (pin version for reproducibility)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for better layer caching
# README.md is needed because pyproject.toml references it
COPY pyproject.toml README.md ./
# Copy lock file if it exists (for reproducible builds)
COPY uv.lock* ./

# Install dependencies (this layer will be cached unless dependencies change)
RUN uv pip install --system --no-cache -e . && \
    rm -rf /root/.cache

# Copy application code (this layer changes most frequently)
COPY src/ src/

# Create runtime directory and set up non-root user
RUN useradd -m -u 1000 powertools && \
    mkdir -p /app/.powertools && \
    chown -R powertools:powertools /app

# Set environment variables
ENV POWERTOOLS_HOST=0.0.0.0 \
    POWERTOOLS_PORT=8765 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER powertools

EXPOSE 8765

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8765/health', timeout=5)" || exit 1

CMD ["python", "-m", "powertools.mcp.server"]
