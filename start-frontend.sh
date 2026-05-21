#!/bin/bash
set -e
cd "$(dirname "$0")/frontend"

if [ ! -d node_modules ]; then
  echo "Instaluję zależności frontendu..."
  npm ci
fi

echo "Uruchamiam frontend: http://localhost:5173"
npm run dev
