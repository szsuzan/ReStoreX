@echo off
echo Starting ReStoreX Backend...
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo [ERROR] Virtual environment not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if .env exists
if not exist ".env" (
    echo [WARNING] .env file not found, using defaults
)

REM Start the server
echo Server starting at http://localhost:3001
echo API Documentation: http://localhost:3001/docs
echo.
echo Press Ctrl+C to stop the server
echo.

python main.py
