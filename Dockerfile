FROM oven/bun:1@sha256:1d22548f177f4ff38e0c15baa3c2c46c6c2060ba2d1bc573bb4720b407548f1d AS frontend

WORKDIR /web
COPY web/package.json web/bun.lock ./
RUN bun install --frozen-lockfile
COPY web/ ./
RUN bun run build


FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim@sha256:531f855bda2c73cd6ef67d56b733b357cea384185b3022bd09f05e002cd144ca AS backend

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
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
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-install-project

COPY . /app
COPY --from=frontend /web/build /app/web/build
COPY --from=frontend /usr/local/bin/bun /usr/local/bin/bun
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

RUN useradd --create-home harpi \
    && mkdir -p /work \
    && chown -R harpi:harpi /app \
    && chown harpi:harpi /work
USER harpi

ENTRYPOINT []

CMD ["/app/.venv/bin/uvicorn", "app:asgi_app", "--app-dir", "/app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
