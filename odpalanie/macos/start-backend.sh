#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON="$PROJECT_ROOT/.venv/bin/python"

if [ ! -f "$PYTHON" ]; then
  echo "Brak .venv. Tworzę lokalne środowisko Python..."

  # Zależności (mediapipe 0.10.21, numpy 1.26.4) działają na Pythonie 3.10–3.12.
  # Szukamy zgodnego interpretera: najpierw 3.11/3.12, potem domyślny python3.
  PYTHON_BIN=""
  for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      ver="$("$candidate" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo "")"
      case "$ver" in
        3.10|3.11|3.12)
          PYTHON_BIN="$candidate"
          break
          ;;
      esac
    fi
  done

  if [ -z "$PYTHON_BIN" ]; then
    echo "Nie znaleziono zgodnego Pythona (wymagany 3.10, 3.11 lub 3.12)."
    echo "Zainstaluj np.: brew install python@3.12"
    exit 1
  fi

  echo "Używam interpretera: $PYTHON_BIN ($("$PYTHON_BIN" --version 2>&1))"
  "$PYTHON_BIN" -m venv "$PROJECT_ROOT/.venv"
fi

echo "Instaluję/aktualizuję zależności backendu..."
"$PYTHON" -m pip install -r "$PROJECT_ROOT/requirements.txt"

echo "Uruchamiam backend: http://127.0.0.1:8000"
exec "$PYTHON" -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
