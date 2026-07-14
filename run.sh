#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8080}"
MODE="${MODE:-run}"  # "edit" or "run"

cleanup() {
    echo "Shutting down..."
    kill "$MARIMO_PID" 2>/dev/null || true
    wait "$MARIMO_PID" 2>/dev/null || true
    sudo tailscale funnel --https=443 off 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting Marimo ($MODE) on port $PORT..."

if [ "$MODE" = "edit" ]; then
    uv run marimo edit main.py \
        --port "$PORT" \
        --host 0.0.0.0 \
        --headless \
        --no-token \
        --no-skew-protection &
else
    uv run marimo run main.py \
        --port "$PORT" \
        --host 0.0.0.0 \
        --headless \
        --no-skew-protection &
fi
MARIMO_PID=$!

# Wait for server to be ready
echo "Waiting for server to start..."
for i in $(seq 1 30); do
    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT" | grep -q "[0-9][0-9][0-9]"; then
        break
    fi
    sleep 1
done

echo "Configuring Tailscale Funnel on port $PORT..."
sudo tailscale funnel --bg "$PORT"

echo ""
echo "Marimo: http://localhost:$PORT"
echo "Public: https://$(hostname).tailf4b715.ts.net/"
echo "Press Ctrl+C to stop."
echo ""

wait "$MARIMO_PID"
