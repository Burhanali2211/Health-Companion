#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Health Companion — Kiosk Mode Launcher
# Launches Chromium in fullscreen kiosk mode pointing at the app
# ═══════════════════════════════════════════════════════════════

# Hide mouse cursor after 3 seconds idle
unclutter -idle 3 -root &

# Wait for backend to be ready
echo "Waiting for Health Companion backend..."
for i in {1..30}; do
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo "Backend is ready!"
        break
    fi
    sleep 1
done

# Launch Chromium in kiosk mode
chromium-browser \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-component-update \
    --check-for-update-interval=31536000 \
    --no-first-run \
    --start-fullscreen \
    --disable-translate \
    --disable-features=TranslateUI \
    --disable-pinch \
    --overscroll-history-navigation=0 \
    --autoplay-policy=no-user-gesture-required \
    --enable-features=OverlayScrollbar \
    http://localhost:8000
