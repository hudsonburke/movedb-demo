#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8080}"
MODE="${MODE:-run}"  # "edit" or "run"
PID_FILE=".marimo.pid"
LOG_FILE=".marimo.log"

# Check if already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Marimo is already running (PID: $OLD_PID)"
        echo "  Stop it with: ./stop.sh"
        echo "  Or: kill $OLD_PID"
        exit 1
    else
        rm -f "$PID_FILE"
    fi
fi

echo "Starting Marimo ($MODE) on port $PORT..."
echo "Logs: $LOG_FILE"

# Start marimo in background
if [ "$MODE" = "edit" ]; then
    nohup uv run marimo edit main.py \
        --port "$PORT" \
        --host 0.0.0.0 \
        --headless \
        --no-token \
        --no-skew-protection > "$LOG_FILE" 2>&1 &
else
    nohup uv run marimo run main.py \
        --port "$PORT" \
        --host 0.0.0.0 \
        --headless \
        --no-skew-protection > "$LOG_FILE" 2>&1 &
fi
MARIMO_PID=$!
echo "$MARIMO_PID" > "$PID_FILE"

# Wait for server to be ready
echo "Waiting for server to start..."
for i in $(seq 1 30); do
    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT" | grep -q "[0-9][0-9][0-9]"; then
        break
    fi
    sleep 1
done

echo "Configuring Tailscale Funnel on port $PORT..."
sudo tailscale funnel --bg "$PORT" 2>/dev/null || true

echo ""
echo "Marimo started in background"
echo "  PID: $MARIMO_PID"
echo "  Local: http://localhost:$PORT"
echo "  Public: https://$(hostname).tailf4b715.ts.net/"
echo ""
echo "To stop: ./stop.sh"
echo "To view logs: tail -f $LOG_FILE"
