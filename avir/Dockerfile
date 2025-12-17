# AVIR Verification Container
#
# This Dockerfile creates an isolated environment for AI-verified testing.
# No source code from the original system - only specifications.

FROM python:3.11-slim

LABEL maintainer="Agentic System Team"
LABEL description="AVIR - AI-Verified Independent Replication"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create verification environment
WORKDIR /verification

# Copy ONLY specifications (no source code)
COPY specs/ /verification/specs/
COPY benchmarks/ /verification/benchmarks/
COPY verify.py /verification/

# Install Python dependencies for verification
RUN pip install --no-cache-dir \
    openai>=1.0.0 \
    google-generativeai>=0.3.0 \
    httpx>=0.24.0 \
    qdrant-client>=1.7.0 \
    sentence-transformers>=2.2.0 \
    aiosqlite>=0.19.0

# Run verification
ENTRYPOINT ["python3", "verify.py"]
