#!/usr/bin/env bash
# ==============================================================================
# Power BI Column-Level Data Lineage - Bare Metal Startup Script
# Designed for Enterprise / Banking environments without Docker.
# ==============================================================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

echo "=========================================================="
echo " Starting Power BI Lineage Service (Host / Bare-Metal)    "
echo "=========================================================="

# 1. Prerequisite Checks
command -v python3 >/dev/null 2>&1 || { echo >&2 "[ERROR] python3 is required but not installed."; exit 1; }
command -v node >/dev/null 2>&1 || { echo >&2 "[ERROR] node (Node.js) is required but not installed."; exit 1; }
command -v npm >/dev/null 2>&1 || { echo >&2 "[ERROR] npm is required but not installed."; exit 1; }

echo "[✓] Prerequisites verified: Python $(python3 --version), Node $(node --version), npm $(npm --version)"

# 2. Setup Python Virtual Environment for Backend
VENV_DIR="$BACKEND_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "[*] Creating Python virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

echo "[*] Activating virtual environment..."
source "$VENV_DIR/bin/activate"

echo "[*] Installing / verifying backend dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r "$BACKEND_DIR/requirements.txt"

# 3. Setup Frontend Dependencies
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "[*] Installing frontend dependencies (npm install)..."
    (cd "$FRONTEND_DIR" && npm install)
fi

# 4. Graceful Cleanup Function
cleanup() {
    echo ""
    echo "[*] Shutting down services..."
    if [ -n "$BACKEND_PID" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    wait 2>/dev/null || true
    echo "[✓] All services stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# 5. Launch Backend (FastAPI on Port 8000)
echo "[*] Starting FastAPI backend on http://127.0.0.1:8000..."
(cd "$BACKEND_DIR" && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000) &
BACKEND_PID=$!

# Wait for backend to be ready
echo "[*] Waiting for backend to respond..."
sleep 2

# 6. Launch Frontend (Vite Dev / Host on Port 3000)
echo "[*] Starting React frontend on http://127.0.0.1:3000..."
(cd "$FRONTEND_DIR" && npm run dev -- --host 0.0.0.0 --port 3000) &
FRONTEND_PID=$!

echo ""
echo "=========================================================="
echo " Applications successfully started!"
echo " - Frontend Web UI:  http://localhost:3000"
echo " - Backend REST API: http://localhost:8000"
echo " - Swagger Docs:     http://localhost:8000/docs"
echo " Press Ctrl+C to stop all services."
echo "=========================================================="

wait
