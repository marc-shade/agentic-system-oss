# Multi-stage production Dockerfile for Synthetic Data MCP Platform
# Optimized for security, performance, and minimal attack surface

ARG PYTHON_VERSION=3.11.10
ARG DEBIAN_VERSION=bookworm

# Stage 1: Security-hardened builder
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION} as builder

# Create build user for security
RUN groupadd -r builder && useradd -r -g builder builder

# Install build dependencies with minimal packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential=12.9 \
    git=1:2.39.2-1.1 \
    curl=7.88.1-10+deb12u8 \
    ca-certificates=20230311 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set secure working directory
WORKDIR /build

# Copy dependency files first for optimal Docker layer caching
COPY --chown=builder:builder pyproject.toml ./
COPY --chown=builder:builder requirements.txt* ./

# Switch to build user
USER builder

# Create virtual environment for isolation
RUN python -m venv /build/venv
ENV PATH="/build/venv/bin:$PATH"

# Install dependencies with security flags
RUN pip install --no-cache-dir --upgrade pip==24.2 setuptools==75.1.0 wheel==0.44.0 && \
    pip install --no-cache-dir --require-hashes --only-binary=all -r pyproject.toml || \
    pip install --no-cache-dir -r pyproject.toml

# Copy application code
COPY --chown=builder:builder src/ ./src/
COPY --chown=builder:builder README.md ./

# Compile Python files for performance
RUN python -m compileall src/

# Stage 2: Minimal production runtime
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION}

# Install security updates and minimal runtime dependencies
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    libpq5=15.8-0+deb12u1 \
    curl=7.88.1-10+deb12u8 \
    ca-certificates=20230311 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /tmp/* /var/tmp/*

# Create application user with minimal privileges
RUN groupadd -r -g 1001 synthetic && \
    useradd -r -u 1001 -g synthetic -d /app -s /bin/false synthetic

# Set secure working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=synthetic:synthetic /build/venv /app/venv

# Copy application code with proper permissions
COPY --from=builder --chown=synthetic:synthetic /build/src /app/src
COPY --from=builder --chown=synthetic:synthetic /build/README.md /app/

# Create application directories with proper permissions
RUN mkdir -p /app/data /app/logs /app/cache /app/tmp && \
    chown -R synthetic:synthetic /app && \
    chmod -R 750 /app

# Add virtual environment to PATH
ENV PATH="/app/venv/bin:$PATH"

# Security and performance environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    SYNTHETIC_DATA_HOME=/app \
    SYNTHETIC_DATA_LOG_LEVEL=INFO \
    SYNTHETIC_DATA_CACHE_DIR=/app/cache \
    SYNTHETIC_DATA_DATA_DIR=/app/data \
    SYNTHETIC_DATA_LOGS_DIR=/app/logs \
    PORT=3000 \
    WORKERS=4 \
    MAX_REQUESTS=10000 \
    MAX_REQUESTS_JITTER=1000 \
    TIMEOUT=300 \
    KEEPALIVE=2

# Security: Drop all privileges and capabilities
USER synthetic

# Health check with improved reliability
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port (changed to 3000 as per requirements)
EXPOSE ${PORT}

# Labels for better container management
LABEL maintainer="marc@2acrestudios.com" \
      org.opencontainers.image.title="Synthetic Data MCP Server" \
      org.opencontainers.image.description="Production-ready synthetic data generation MCP server" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.vendor="2 Acre Studios" \
      org.opencontainers.image.url="https://github.com/marc-shade/synthetic-data-mcp" \
      org.opencontainers.image.source="https://github.com/marc-shade/synthetic-data-mcp" \
      org.opencontainers.image.schema-version="1.0"

# Production startup with proper signal handling
CMD ["python", "-m", "synthetic_data_mcp.server"]