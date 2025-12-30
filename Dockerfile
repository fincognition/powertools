FROM python:3.12-slim

WORKDIR /app

# Version for hatch-vcs (passed as build arg since .git is not available in Docker)
ARG VERSION=0.0.0
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${VERSION}

# Install uv (pin version for reproducibility)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy all source files needed for install
COPY pyproject.toml README.md ./
COPY uv.lock* ./
COPY src/ src/

# Install package (not editable - production build)
RUN uv pip install --system --no-cache . && \
    rm -rf /root/.cache

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
