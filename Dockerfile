# Parametric Dockerfile for running scripts with specific extras
# Usage:
#   docker build -t fai-script-pdf --build-arg EXTRAS=pdf --build-arg SCRIPT=ingest_pdf.py .
#   docker run --rm -it -v "$PWD/data:/app/scripts/data" fai-script-pdf

# Build arguments for parametric behavior
ARG EXTRAS=""
ARG SCRIPT="ingest_pdf.py"

# Add <builder-digest> in prod
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Pass build args to builder stage
ARG EXTRAS
ARG SCRIPT

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Install system dependencies for PDF processing (if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for better caching
COPY uv.lock pyproject.toml ./

# Install dependencies based on EXTRAS parameter
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ -n "$EXTRAS" ]; then \
        echo "Installing with extras: $EXTRAS"; \
        # Split extras by comma and install each one
        for extra in $(echo "$EXTRAS" | tr ',' ' '); do \
            echo "Installing extra: $extra"; \
            uv sync --locked --no-install-project --extra "$extra" --no-dev --no-editable; \
        done; \
    else \
        echo "Installing base dependencies only"; \
        uv sync --locked --no-install-project --no-dev --no-editable; \
    fi

# Copy the entire project
COPY . /app

# Install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ -n "$EXTRAS" ]; then \
        # Split extras by comma and install each one
        for extra in $(echo "$EXTRAS" | tr ',' ' '); do \
            echo "Installing project with extra: $extra"; \
            uv sync --locked --extra "$extra" --no-dev --no-editable; \
        done; \
    else \
        uv sync --locked --no-dev --no-editable; \
    fi

# Clean up cache
RUN rm -rf /root/.cache/uv /root/.cache/pip

# Add <runtime-digest> in prod
FROM python:3.12-slim-bookworm AS runtime

# Pass build args to runtime stage
ARG EXTRAS
ARG SCRIPT

# Install runtime system dependencies for PDF processing (if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

ENV PIP_NO_CACHE_DIR=1 \
    UV_PYTHON_DOWNLOADS=0 \
    SCRIPT_NAME="$SCRIPT"

# Create non-root user
RUN groupadd -r app && \
    useradd -r -g app -d /nonexistent -s /usr/sbin/nologin app

# Copy built application from builder stage
COPY --from=builder --chown=app:app /app /app

# Set working directory and PATH
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"

# Switch to non-root user
USER app

# Validate that the script exists
RUN test -f "/app/scripts/$SCRIPT" || (echo "Error: Script /app/scripts/$SCRIPT not found" && exit 1)

# Default command runs the specified script
CMD ["sh", "-c", "cd /app/scripts && python \"$SCRIPT_NAME\""]