#!/bin/bash


HOST="0.0.0.0"
PORT="8000"

while true; do
    echo "checando atualizações..."
    uv sync --upgrade
    echo "Inciando Harpi..."
    uv run uvicorn app:asgi_app --host "${HOST}" --port "${PORT}" --reload
    echo "Harpi parou. Reiniciando em 5 segundos..."

    for i in {5..1}; do
        echo "Reiniciando em $i segundos..."
        sleep 1
    done
done
