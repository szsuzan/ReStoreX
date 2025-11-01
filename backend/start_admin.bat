@echo off
REM Run ReStoreX Backend with Administrator Rights

echo ============================================
echo ReStoreX Backend - Starting with Admin Rights
echo ============================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Running with Administrator rights
    echo.
) else (
    echo [ERROR] Not running as Administrator!
    echo Please right-click this file and select "Run as administrator"
    echo.
    pause
    exit /b 1
)

REM Navigate to backend directory
cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "venv\" (
    echo [ERROR] Virtual environment not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Activate virtual environment and start backend
echo Starting backend server...
echo.
call venv\Scripts\activate.bat
python main.py

pause
