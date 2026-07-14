#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8080}"

cleanup() {
	echo "Shutting down Marimo..."
	kill "$MARIMO_PID" 2>/dev/null || true
	wait "$MARIMO_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting Marimo on port $PORT..."
uv run marimo run main.py \
	--port "$PORT" \
	--headless \
	--no-skew-protection &
MARIMO_PID=$!

echo "Configuring Tailscale Funnel on port $PORT..."
tailscale funnel "$PORT"

echo ""
echo "Marimo: http://localhost:$PORT"
echo "Press Ctrl+C to stop."
echo ""

wait "$MARIMO_PID"
