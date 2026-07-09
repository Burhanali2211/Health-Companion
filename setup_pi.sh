#!/bin/bash

echo "=============================================="
echo "    Watan Sehat - Raspberry Pi Auto Setup     "
echo "=============================================="

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo "[1/4] Installing system dependencies (PyQt6 & Venv)..."
sudo apt-get update
sudo apt-get install -y python3-pyqt6 python3-pyqt6.qtwebengine python3-venv curl

echo ""
echo "[2/4] Setting up Python Virtual Environment..."
cd "$DIR/backend" || exit
# Remove broken venv if it exists
if [ -d "venv" ]; then
    echo "Found existing venv, updating it..."
fi
python3 -m venv --system-site-packages venv
source venv/bin/activate

echo ""
echo "[3/4] Installing Python requirements..."
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

echo ""
echo "[4/4] Checking Ollama AI Installation..."
if ! command -v ollama &> /dev/null
then
    echo "Ollama is not installed. Installing Ollama for local AI..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "Ollama is already installed."
fi

# Ensure ollama service is running
sudo systemctl enable ollama
sudo systemctl start ollama

echo ""
echo "[5/5] Downloading Local AI Model (qwen2.5:1.5b)..."
echo "This might take a few minutes depending on your internet connection."
ollama pull qwen2.5:1.5b

echo "=============================================="
echo " Setup Complete! You can now run the app via: "
echo " ./run_app.sh                                 "
echo "=============================================="
