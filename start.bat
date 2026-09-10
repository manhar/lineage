@echo off
REM ==============================================================================
REM Power BI Column-Level Data Lineage - Windows Startup Script
REM Designed for Enterprise / Banking environments on Windows Server without Docker.
REM ==============================================================================

echo ==========================================================
echo  Starting Power BI Lineage Service (Windows Server)
echo ==========================================================

REM 1. Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b 1
)

REM 2. Check Node
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH.
    pause
    exit /b 1
)

set PROJECT_DIR=%~dp0
set BACKEND_DIR=%PROJECT_DIR%backend
set FRONTEND_DIR=%PROJECT_DIR%frontend

REM 3. Virtual Environment Setup
if not exist "%BACKEND_DIR%\.venv" (
    echo [*] Creating Python virtual environment...
    python -m venv "%BACKEND_DIR%\.venv"
)

call "%BACKEND_DIR%\.venv\Scripts\activate.bat"
echo [*] Installing backend dependencies...
pip install -r "%BACKEND_DIR%\requirements.txt"

REM 4. Frontend setup
if not exist "%FRONTEND_DIR%\node_modules" (
    echo [*] Installing frontend packages...
    cd "%FRONTEND_DIR%"
    call npm install
    cd "%PROJECT_DIR%"
)

REM 5. Start Backend in new window
echo [*] Starting Backend service...
start "Lineage Backend API (Port 8000)" cmd /k "cd %BACKEND_DIR% && call .venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

REM 6. Start Frontend in new window
echo [*] Starting Frontend service...
start "Lineage Frontend UI (Port 3000)" cmd /k "cd %FRONTEND_DIR% && npm run dev -- --host 0.0.0.0 --port 3000"

echo ==========================================================
echo  Services launched in background windows!
echo  - Frontend Web UI:  http://localhost:3000
echo  - Backend REST API: http://localhost:8000
echo  - Swagger Docs:     http://localhost:8000/docs
echo ==========================================================
