# Add <builder-digest> in prod
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --all-extras --no-dev --no-editable
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --all-extras --no-dev --no-editable
RUN rm -rf /root/.cache/uv /root/.cache/pip

# Add <runtime-digest> in prod
FROM python:3.12-slim-bookworm AS runtime

ENV PIP_NO_CACHE_DIR=1 \
    UV_PYTHON_DOWNLOADS=0
RUN groupadd -r app && \
    useradd -r -g app -d /nonexistent -s /usr/sbin/nologin app
USER app
WORKDIR /app
COPY --from=builder --chown=app:app /app /app
ENV PATH="/app/.venv/bin:$PATH"
CMD ["/app/.venv/bin/flare-ai-kit"]