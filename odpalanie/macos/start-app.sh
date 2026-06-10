#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT"

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "=== Cyber Trener — uruchamianie backendu i frontendu ==="
echo "Backend:  http://127.0.0.1:8000"
echo "Frontend: http://localhost:5173"
echo "Zatrzymaj: Ctrl+C"
echo ""

PYTHON="$PROJECT_ROOT/.venv/bin/python"
if [[ ! -f "$PYTHON" ]]; then
  if ! command -v python3.11 >/dev/null 2>&1; then
    echo "Nie znaleziono python3.11. Zainstaluj Python 3.11 (np. brew install python@3.11)."
    exit 1
  fi
  python3.11 -m venv "$PROJECT_ROOT/.venv"
fi

echo "[1/2] Backend..."
"$PYTHON" -m pip install -q -r "$PROJECT_ROOT/requirements.txt"
"$PYTHON" -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

sleep 2

echo "[2/2] Frontend..."
cd "$PROJECT_ROOT/frontend"
npm install --silent
exec npm run dev
