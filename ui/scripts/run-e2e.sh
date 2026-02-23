#!/bin/bash
set -e

echo "Starting backend server on port 5000..."
uv run uvicorn app:asgi_app --host "0.0.0.0" --port "8000" --reload &
BACKEND_PID=$!

sleep 3

echo "Starting frontend server on port 3000..."
cd ./ui && bun run dev --port 3000 &
FRONTEND_PID=$!

sleep 5

echo "Running Playwright tests..."
cd ui && bunx playwright test

TEST_EXIT_CODE=$?

echo "Cleaning up..."
kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
sudo kill -9 $(sudo lsof -t -i:3000)
sudo kill -9 $(sudo lsof -t -i:8000)


exit $TEST_EXIT_CODE
