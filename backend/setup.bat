@echo off
echo ================================
echo ReStoreX Backend Setup
echo ================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/5] Checking Python installation...
python --version

REM Check if virtual environment exists
if not exist "venv" (
    echo.
    echo [2/5] Creating virtual environment...
    python -m venv venv
) else (
    echo.
    echo [2/5] Virtual environment already exists
)

echo.
echo [3/5] Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo [4/5] Installing dependencies...
pip install -r requirements.txt

REM Create .env if it doesn't exist
if not exist ".env" (
    echo.
    echo [5/5] Creating .env file...
    copy .env.example .env
    echo Please edit .env file to configure your settings
) else (
    echo.
    echo [5/5] .env file already exists
)

echo.
echo ================================
echo Setup Complete!
echo ================================
echo.
echo Next steps:
echo 1. Make sure TestDisk is installed and in PATH
echo 2. Edit .env file if needed
echo 3. Run: python main.py
echo.
pause
