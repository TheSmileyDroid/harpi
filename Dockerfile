# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    unzip \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Bun
RUN curl -fsSL https://bun.sh/install | bash

# Add Bun to PATH
ENV PATH="/root/.bun/bin:${PATH}"

# Copy Python requirements first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy frontend package files
COPY frontend/package.json frontend/bun.lockb ./frontend/

# Install frontend dependencies
WORKDIR /app/frontend
RUN bun install

# Copy the rest of the application
WORKDIR /app
COPY . .

# Build frontend
WORKDIR /app/frontend
RUN bun run build

# Switch back to app directory
WORKDIR /app

# Expose port
EXPOSE ${PORT}

# Command to run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "${PORT}"]
