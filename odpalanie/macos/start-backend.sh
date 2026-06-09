#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON="$PROJECT_ROOT/.venv/bin/python"

if [ ! -f "$PYTHON" ]; then
  echo "Brak .venv. Tworzę lokalne środowisko Python..."
  if ! command -v python3.11 >/dev/null 2>&1; then
    echo "Nie znaleziono python3.11. Zainstaluj Python 3.11 (np. brew install python@3.11)."
    exit 1
  fi
  python3.11 -m venv "$PROJECT_ROOT/.venv"
fi

echo "Instaluję/aktualizuję zależności backendu..."
"$PYTHON" -m pip install -r "$PROJECT_ROOT/requirements.txt"

echo "Uruchamiam backend: http://127.0.0.1:8000"
exec "$PYTHON" -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
