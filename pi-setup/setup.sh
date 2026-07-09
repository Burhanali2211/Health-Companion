#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Health Companion — Raspberry Pi 5 Full Setup Script
# Run: sudo bash pi-setup/setup.sh
# ═══════════════════════════════════════════════════════════════

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo "══════════════════════════════════════════════════"
echo "  وطن صحت — Health Companion Pi Setup"
echo "══════════════════════════════════════════════════"
echo ""

# ─── 1. System Updates ──────────────────────────────────────
echo "[1/6] Updating system packages..."
sudo apt update && sudo apt upgrade -y

# ─── 2. Install System Dependencies ─────────────────────────
echo "[2/6] Installing system dependencies..."
sudo apt install -y \
    python3-pip python3-venv python3-dev \
    libasound2-dev portaudio19-dev \
    chromium-browser \
    unclutter \
    git curl wget

# ─── 3. Python Virtual Environment ──────────────────────────
echo "[3/6] Setting up Python virtual environment..."
cd "$PROJECT_DIR/backend"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# ─── 4. Install Node.js & Build Frontend ────────────────────
echo "[4/6] Installing Node.js and building frontend..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt install -y nodejs
fi
cd "$PROJECT_DIR/frontend"
npm install
npm run build
# Copy built frontend to backend/static for single-server serving
rm -rf "$PROJECT_DIR/backend/static"
cp -r "$PROJECT_DIR/frontend/dist" "$PROJECT_DIR/backend/static"
echo "  Frontend built and copied to backend/static/"

# ─── 5. Install Ollama & Pull Model ─────────────────────────
echo "[5/6] Installing Ollama for offline AI..."
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
fi
# Start Ollama service
sudo systemctl enable ollama 2>/dev/null || true
sudo systemctl start ollama 2>/dev/null || true
sleep 3

echo "  Pulling qwen2.5:0.5b model (this takes a few minutes)..."
ollama pull qwen2.5:0.5b

# ─── 6. Install Systemd Services ────────────────────────────
echo "[6/6] Installing systemd services..."

# Health Companion Backend Service
cat > /etc/systemd/system/watan-sehat.service << EOF
[Unit]
Description=Health Companion Backend
After=network.target ollama.service
Wants=ollama.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR/backend
ExecStart=$PROJECT_DIR/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
Environment=WATAN_OLLAMA_MODEL=qwen2.5:0.5b

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable watan-sehat

echo ""
echo "══════════════════════════════════════════════════"
echo "  ✓ Setup complete!"
echo ""
echo "  Start backend:  sudo systemctl start watan-sehat"
echo "  View logs:      journalctl -u watan-sehat -f"
echo "  Open kiosk:     bash pi-setup/kiosk.sh"
echo "══════════════════════════════════════════════════"
echo ""
