#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LLM_DIR="$(cd "$SCRIPT_DIR/../../free-claude-code" 2>/dev/null && pwd || echo "")"

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║          METHER OS — STARTING            ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

PIDS=()

cleanup() {
    echo ""
    echo "  [METHER] Shutting down all services..."
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null
    echo "  [METHER] All services stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start LLM proxy
if [ -n "$LLM_DIR" ] && [ -d "$LLM_DIR" ]; then
    echo "  [METHER] Starting LLM Proxy on :8082..."
    (cd "$LLM_DIR" && uv run uvicorn server:app --host 0.0.0.0 --port 8082) &
    PIDS+=($!)
    sleep 3
else
    echo "  [WARN]   LLM Proxy directory not found — skipping."
fi

# Start backend
echo "  [METHER] Starting Backend on :8000..."
(cd "$ROOT_DIR/backend" && uvicorn src.mether.main:app --host 0.0.0.0 --port 8000) &
PIDS+=($!)
sleep 2

# Start WhatsApp sidecar
if [ -f "$ROOT_DIR/whatsapp/src/index.js" ]; then
    echo "  [METHER] Starting WhatsApp Bridge on :3001..."
    (cd "$ROOT_DIR/whatsapp" && node src/index.js) &
    PIDS+=($!)
fi

# Start voice sidecar
if [ -f "$ROOT_DIR/voice/src/main.py" ]; then
    echo "  [METHER] Starting Voice Pipeline..."
    (cd "$ROOT_DIR/voice" && python src/main.py) &
    PIDS+=($!)
fi

sleep 2

# Start frontend
echo "  [METHER] Starting Frontend on :5173..."
(cd "$ROOT_DIR/frontend" && npm run dev) &
PIDS+=($!)

sleep 3

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║        METHER OS — ALL SERVICES UP       ║"
echo "  ╠══════════════════════════════════════════╣"
echo "  ║  Dashboard:  http://localhost:5173       ║"
echo "  ║  Backend:    http://localhost:8000       ║"
echo "  ║  LLM Proxy:  http://localhost:8082       ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""
echo "  Press Ctrl+C to stop all services."

# Wait for all background processes
wait
