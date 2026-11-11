#!/usr/bin/env bash
# AI Gallery 2.0 — start the server (unless it already runs) and open the browser.
cd "$(dirname "$0")"
PORT="${PORT:-8924}"
URL="http://127.0.0.1:${PORT}"

if curl -sf "${URL}/api/health" >/dev/null 2>&1; then
  xdg-open "${URL}" >/dev/null 2>&1
  exit 0
fi

( for _ in $(seq 120); do
    curl -sf "${URL}/api/health" >/dev/null 2>&1 && { xdg-open "${URL}" >/dev/null 2>&1; break; }
    sleep 0.5
  done ) &

exec ./run.sh
