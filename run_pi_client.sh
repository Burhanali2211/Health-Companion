#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Health Companion — Raspberry Pi Client Kiosk Auto-Launcher
# ═══════════════════════════════════════════════════════════════

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
CONFIG_FILE="$DIR/.pi_server_config"

# Allow overriding via command line argument
if [ ! -z "$1" ]; then
    echo "$1" > "$CONFIG_FILE"
    echo "Saved new server IP: $1"
fi

SERVER_IP=""
if [ -f "$CONFIG_FILE" ]; then
    SERVER_IP=$(cat "$CONFIG_FILE")
fi

if [ ! -z "$SERVER_IP" ]; then
    echo "=================================================="
    echo " Saved Server IP: $SERVER_IP"
    echo " To change this, run: ./run_pi_client.sh <new_ip>"
    echo " Or press 'c' and hit Enter within 3 seconds to change..."
    echo "=================================================="
    if read -t 3 -n 1 -r KEY; then
        if [[ "$KEY" == "c" || "$KEY" == "C" ]]; then
            SERVER_IP=""
        fi
    fi
fi

if [ -z "$SERVER_IP" ]; then
    echo ""
    echo "Enter Host PC IP Address (e.g. 192.168.1.232):"
    read -r SERVER_IP
    echo "$SERVER_IP" > "$CONFIG_FILE"
fi

echo ""
echo "Updating client codebase..."
git pull || echo "Warning: git pull failed, starting with cached code..."

# Create Desktop Shortcut if running on Raspberry Pi GUI
DESKTOP_DIR="$HOME/Desktop"
if [ -d "$DESKTOP_DIR" ]; then
    SHORTCUT="$DESKTOP_DIR/WatanSehatClient.desktop"
    if [ ! -f "$SHORTCUT" ]; then
        echo "Creating Desktop shortcut for touch screen..."
        cat << EOF > "$SHORTCUT"
[Desktop Entry]
Name=Watan Sehat Kiosk
Comment=Launch Health Kiosk Client
Exec=bash -c "$DIR/run_pi_client.sh"
Icon=utilities-terminal
Terminal=true
Type=Application
Categories=Utility;
EOF
        chmod +x "$SHORTCUT"
        echo "Shortcut created on Desktop successfully!"
    fi
fi

# Activate virtual environment if available
if [ -f "$DIR/backend/venv/bin/activate" ]; then
    source "$DIR/backend/venv/bin/activate"
fi

cd "$DIR/native_app" || exit
echo "Launching GUI connected to http://$SERVER_IP:8000..."
python3 main_window.py --server "http://$SERVER_IP:8000"
