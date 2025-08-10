# -----------------
# FRONTEND
# -----------------
FROM oven/bun:latest AS frontend

WORKDIR /app/frontend

# Install deps first (cached between builds)
COPY frontend/package.json frontend/bun.lockb ./
RUN bun install

# Copy source and build for production
COPY frontend .
RUN bun run build


# -----------------
# BACKEND
# -----------------
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS backend

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install backend deps first (cached)
COPY uv.lock pyproject.toml ./
RUN rm -rf .venv && uv sync --upgrade

# Copy backend source
COPY . .

ENV PATH="/app/.venv/bin:$PATH"

# Default command (can be overridden in docker-compose)
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
