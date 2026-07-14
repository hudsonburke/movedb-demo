#!/usr/bin/env bash
set -euo pipefail

PID_FILE=".marimo.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "No PID file found. Marimo may not be running."
    exit 0
fi

PID=$(cat "$PID_FILE")

if kill -0 "$PID" 2>/dev/null; then
    echo "Stopping Marimo (PID: $PID)..."
    kill "$PID"
    # Wait for process to stop
    for i in $(seq 1 10); do
        if ! kill -0 "$PID" 2>/dev/null; then
            break
        fi
        sleep 0.5
    done
    # Force kill if still running
    if kill -0 "$PID" 2>/dev/null; then
        echo "Force killing..."
        kill -9 "$PID" 2>/dev/null || true
    fi
    echo "Stopped."
else
    echo "Marimo is not running (stale PID file)."
fi

rm -f "$PID_FILE"
sudo tailscale funnel --https=443 off 2>/dev/null || true
