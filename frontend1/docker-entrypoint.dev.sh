#!/bin/sh
set -e
cd /app
if [ ! -f node_modules/.bin/next ]; then
  echo "[docker-dev] Installing npm dependencies..."
  npm ci
fi
exec npm run dev -- --hostname 0.0.0.0 --port 3000
