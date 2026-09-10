@echo off
REM ==============================================================================
REM Power BI Column-Level Data Lineage - Windows Python Runner
REM Designed for Enterprise / Banking environments with Python ONLY.
REM ==============================================================================

echo ==========================================================
echo  Power BI Lineage Service - 100%% Python Edition
echo  (No Docker, No Node.js required)
echo ==========================================================

REM 1. Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b 1
)

set PROJECT_DIR=%~dp0
set VENV_DIR=%PROJECT_DIR%.venv

REM 2. Virtual Environment Setup
if not exist "%VENV_DIR%" (
    echo [*] Creating Python virtual environment...
    python -m venv "%VENV_DIR%"
)

call "%VENV_DIR%\Scripts\activate.bat"
echo [*] Installing backend dependencies...
pip install -r "%PROJECT_DIR%backend\requirements.txt"

REM 3. Launch Unified Python Service
echo ==========================================================
echo  Service running at http://localhost:8000
echo  Press Ctrl+C to stop.
echo ==========================================================

python "%PROJECT_DIR%run.py" --host 0.0.0.0 --port 8000
pause
