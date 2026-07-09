#!/bin/bash

echo "Starting Health Companion Native App on Raspberry Pi..."

# Get the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Activate the virtual environment in the backend folder
if [ -f "$DIR/backend/venv/bin/activate" ]; then
    source "$DIR/backend/venv/bin/activate"
else
    echo "Warning: Virtual environment not found at backend/venv/bin/activate"
    echo "Attempting to run with system Python..."
fi

# Navigate to the native_app folder and run the app
cd "$DIR/native_app" || exit
python3 main_window.py

if [ $? -ne 0 ]; then
    echo ""
    echo "The application crashed or failed to start."
    echo "Check crash.log for details."
    read -p "Press enter to continue..."
fi
