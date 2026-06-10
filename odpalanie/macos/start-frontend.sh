#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT/frontend"

echo "Instaluję/aktualizuję zależności frontendu..."
npm install

echo "Uruchamiam frontend: http://localhost:5173"
exec npm run dev
