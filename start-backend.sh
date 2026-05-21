#!/bin/bash
set -e
cd "$(dirname "$0")"

PYTHON=".venv/bin/python"
if [ ! -f "$PYTHON" ]; then
  echo "Brak .venv — utwórz: python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

echo "Uruchamiam backend: http://127.0.0.1:8000"
exec "$PYTHON" -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload
