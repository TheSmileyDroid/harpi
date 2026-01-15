FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS backend

# System deps
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    unzip \
    && rm -rf /var/lib/apt/lists/*


ENV DENO_INSTALL=/usr/local
RUN curl -fSL https://deno.land/install.sh |  sh -s -- --yes

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV UV_TOOL_BIN_DIR=/usr/local/bin

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --upgrade --no-install-project

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --upgrade

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT []

# Default command
CMD ["uv", "run", "uvicorn", "app:asgi_app", "--host", "0.0.0.0", "--port", "8000"]
