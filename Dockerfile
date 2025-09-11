# Parametric Dockerfile for Flare AI Kit Scripts
# Build args:
#   EXTRAS: comma-separated list of optional dependency groups (e.g., "pdf,rag,a2a")
#   SCRIPT: script name to run (e.g., "pdf_ingestion", "rag_vector_demo")
#
# Example usage:
#   docker build -t fai-script-pdf --build-arg EXTRAS=pdf --build-arg SCRIPT=pdf_ingestion .
#   docker run --rm -it -v "$PWD/data:/app/scripts/data" fai-script-pdf

# Build arguments with defaults
ARG EXTRAS=""
ARG SCRIPT="ftso_price"

# Add <builder-digest> in prod
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Set build args as env vars for the build stage
ARG EXTRAS
ARG SCRIPT
ENV EXTRAS=${EXTRAS} \
    SCRIPT=${SCRIPT} \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Copy dependency files first for better caching
COPY uv.lock pyproject.toml README.md ./

# Install dependencies based on EXTRAS build arg
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ -n "$EXTRAS" ]; then \
        echo "Installing with extras: $EXTRAS" && \
        uv sync --locked --no-install-project --extra="$EXTRAS" --no-dev --no-editable; \
    else \
        echo "Installing base dependencies only" && \
        uv sync --locked --no-install-project --no-dev --no-editable; \
    fi

# Copy source code and scripts
COPY src/ ./src/
COPY scripts/ ./scripts/

# Install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ -n "$EXTRAS" ]; then \
        uv sync --locked --extra="$EXTRAS" --no-dev --no-editable; \
    else \
        uv sync --locked --no-dev --no-editable; \
    fi

# Validate that the specified script exists
RUN if [ ! -f "scripts/${SCRIPT}.py" ]; then \
        echo "Error: Script 'scripts/${SCRIPT}.py' not found!" && \
        echo "Available scripts:" && \
        ls -la scripts/*.py && \
        exit 1; \
    fi

# Clean up caches
RUN rm -rf /root/.cache/uv /root/.cache/pip

# Runtime stage
FROM python:3.12-slim-bookworm AS runtime

# Build args need to be redeclared in each stage
ARG EXTRAS
ARG SCRIPT

# Install system dependencies for specific extras
RUN apt-get update && \
    if echo "$EXTRAS" | grep -q "pdf"; then \
        echo "Installing PDF processing dependencies..." && \
        apt-get install -y --no-install-recommends \
            tesseract-ocr \
            tesseract-ocr-eng \
            poppler-utils \
            libgl1-mesa-glx \
            libglib2.0-0; \
    fi && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r app && \
    useradd -r -g app -d /nonexistent -s /usr/sbin/nologin app

# Set environment variables
ENV PIP_NO_CACHE_DIR=1 \
    UV_PYTHON_DOWNLOADS=0 \
    SCRIPT=${SCRIPT} \
    EXTRAS=${EXTRAS}

# Copy application from builder
WORKDIR /app
COPY --from=builder --chown=app:app /app /app

# Set PATH to include virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Create data directory for script I/O
RUN mkdir -p /app/scripts/data && chown -R app:app /app/scripts/data

# Switch to non-root user
USER app

# Validate script exists and can be imported
RUN python -c "import sys; sys.path.insert(0, '/app/src'); import importlib.util; spec = importlib.util.spec_from_file_location('script', '/app/scripts/${SCRIPT}.py'); print(f'Script ${SCRIPT}.py is ready to run')"

# Default command runs the specified script
CMD python /app/scripts/${SCRIPT}.py