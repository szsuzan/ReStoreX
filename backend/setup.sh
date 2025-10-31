#!/bin/bash

echo "================================"
echo "ReStoreX Backend Setup"
echo "================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed"
    echo "Please install Python 3.8+ first"
    exit 1
fi

echo "[1/5] Checking Python installation..."
python3 --version

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo "[2/5] Creating virtual environment..."
    python3 -m venv venv
else
    echo ""
    echo "[2/5] Virtual environment already exists"
fi

echo ""
echo "[3/5] Activating virtual environment..."
source venv/bin/activate

echo ""
echo "[4/5] Installing dependencies..."
pip install -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo ""
    echo "[5/5] Creating .env file..."
    cp .env.example .env
    echo "Please edit .env file to configure your settings"
else
    echo ""
    echo "[5/5] .env file already exists"
fi

echo ""
echo "================================"
echo "Setup Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Make sure TestDisk is installed and in PATH"
echo "2. Edit .env file if needed"
echo "3. Run: python main.py"
echo ""
