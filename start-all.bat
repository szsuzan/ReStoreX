@echo off
title ReStoreX - Starting Services
color 0A

echo.
echo  ====================================================
echo         Starting ReStoreX Application
echo  ====================================================
echo.

REM Check if backend exists
if not exist "backend" (
    echo [ERROR] Backend folder not found!
    echo Please ensure you're in the ReStoreX root directory
    pause
    exit /b 1
)

REM Check if frontend exists
if not exist "frontend" (
    echo [ERROR] Frontend folder not found!
    echo Please ensure you're in the ReStoreX root directory
    pause
    exit /b 1
)

echo [1/4] Checking backend setup...
if not exist "backend\venv" (
    echo [ERROR] Backend not set up! Running setup...
    cd backend
    call setup.bat
    cd ..
)

echo [2/4] Starting backend server...
start "ReStoreX Backend" cmd /k "cd backend && venv\Scripts\activate && python main.py"

echo [3/4] Waiting for backend to start...
timeout /t 5 /nobreak >nul

echo [4/4] Starting frontend...
start "ReStoreX Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo  ====================================================
echo         ReStoreX Application Started!
echo  ====================================================
echo.
echo  Backend:  http://localhost:3001
echo  Frontend: http://localhost:5173
echo  API Docs: http://localhost:3001/docs
echo.
echo  Two command windows have been opened:
echo  1. Backend Server (Python/FastAPI)
echo  2. Frontend Server (Vite/React)
echo.
echo  Close those windows to stop the services
echo  ====================================================
echo.
pause
