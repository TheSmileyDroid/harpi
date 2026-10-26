FROM oven/bun:1 AS frontend

WORKDIR /web
COPY web/package.json web/bun.lock ./
RUN bun install --frozen-lockfile
COPY web/ ./
RUN bun run build


FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS backend

RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    unzip \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV UV_TOOL_BIN_DIR=/usr/local/bin
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --upgrade --no-install-project

COPY . /app
COPY --from=frontend /web/build /app/web/build
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --upgrade

RUN useradd --create-home harpi \
    && mkdir -p /work \
    && chown -R harpi:harpi /app \
    && chown harpi:harpi /work
USER harpi

ENTRYPOINT []

CMD ["/app/.venv/bin/uvicorn", "app:asgi_app", "--app-dir", "/app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
