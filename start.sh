#!/usr/bin/env bash
# ==============================================================================
# Power BI Column-Level Data Lineage - 100% Python Runner
# Designed for Banking / Enterprise environments with Python ONLY.
# ==============================================================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
VENV_DIR="$PROJECT_DIR/.venv"

echo "=========================================================="
echo " Power BI Lineage Service - 100% Python Edition           "
echo " (No Docker, No Node.js required on host server)         "
echo "=========================================================="

# 1. Prerequisite Check (Python 3 only)
command -v python3 >/dev/null 2>&1 || { echo >&2 "[ERROR] python3 is required but not installed."; exit 1; }
echo "[✓] Python verified: $(python3 --version)"

# 2. Virtual Environment Setup
if [ ! -d "$VENV_DIR" ]; then
    echo "[*] Creating Python virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

echo "[*] Activating virtual environment..."
source "$VENV_DIR/bin/activate"

echo "[*] Installing / verifying Python dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r "$BACKEND_DIR/requirements.txt"

# 3. Launch Unified Python Service
echo ""
echo "=========================================================="
echo " Starting Unified Service on Port 8000...                "
echo " - Web UI & Canvas:   http://localhost:8000              "
echo " - REST API:          http://localhost:8000/api/lineage  "
echo " - Swagger Docs:      http://localhost:8000/docs         "
echo " Press Ctrl+C to stop the service.                       "
echo "=========================================================="
echo ""

python "$PROJECT_DIR/run.py" --host 0.0.0.0 --port 8000
