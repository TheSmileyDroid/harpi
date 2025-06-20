FROM oven/bun:latest as frontend

COPY frontend /app/frontend
# Set working directory
WORKDIR /app/frontend

# Install bun
RUN curl -fsSL https://bun.sh/install | bash
ENV PATH="/root/.bun/bin:${PATH}"

# Copy frontend package files
COPY frontend/package.json frontend/bun.lockb ./

# Install frontend dependencies
RUN bun install

RUN bun run build

# Python backend
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim as backend

COPY . /app
WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=frontend /app/frontend/dist ./static
COPY uv.lock .
RUN uv sync --upgrade

ENV PATH="/app/.venv/bin:$PATH"
